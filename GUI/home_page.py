import flet as ft

from encryptions import EncryptedTransport
from Caches.user_cache import ClientSideUserCache

from GUI.Controls.navigation_sidebar import NavigationSidebar

from pseudo_http_protocol import ClientMessage


class HomePage:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.LIGHT

        # these sizes are the optimal ratio for the average PC screen
        self.page_width = 1280
        self.page_height = 720

        self.transport: EncryptedTransport | None = None
        if hasattr(page, "transport"):
            self.transport: EncryptedTransport = page.transport

        # this holds the session token (which is the authentication)
        self.user_cache: ClientSideUserCache | None = None
        if hasattr(page, "user_cache"):
            self.user_cache: ClientSideUserCache = page.user_cache

        self.sidebar = NavigationSidebar(page=page)
        # override the on_click method so that clicking on the button does not reset the information already input
        self.sidebar.goto_home_page.on_click = None
        # the sidebar is set to 2 and the right side of the page is set to 10. this means the sidebar takes 20% of the available screen
        self.sidebar.expand = 2

        self.song_items: dict[int, dict[str, ft.Container | str | int]]
        """
        dict[
            song ID, dict[
                "item": container
                "artist_name": str,
                "album_name": str,
                "song_name": str,
                "song_length": int, (milliseconds),
                "genres": list[str]
            ]
        ]
        """

        self.loading_song_items: dict[int, ft.Container] = {}

        self._initialize_controls()

    @staticmethod
    def _create_loading_item(song_id: int) -> ft.Container:
        song_cover_art_loading = ft.Container(
            width=120,
            height=150,
            bgcolor=ft.Colors.GREY,
            content=ft.Container(
                width=20,
                height=20,
                content=ft.ProgressRing(
                    color=ft.Colors.BLACK,
                )
            ),
            alignment=ft.Alignment(0, 0)
        )

        song_item_load: ft.Container = ft.Container(
            width=200,
            height=200,
            border_radius=5,
            bgcolor=ft.Colors.GREY_200,
            padding=10,
            content=ft.Row(
                [
                    song_cover_art_loading,
                    ft.Column(
                        [
                            ft.Container(
                                height=20,
                                width=100,
                                bgcolor=ft.Colors.GREY_800
                            ),
                        ]
                    )
                ],
                vertical_alignment=ft.CrossAxisAlignment.START
            ),
            data={
                "song_id": song_id
            }
        )

        return song_item_load

    def _add_song_item(self, item: ft.Container):
        self.song_item_gridview.controls.append(item)

        self.song_item_gridview.update()

    def add_song_info(
            self,
            song_id: int,
            artist_name: str,
            album_name: str,
            song_name: str,
            song_length: int,
            genres: list[str],
    ):
        loading_song_item: ft.Container = self._create_loading_item(song_id=song_id)
        self._add_song_item(loading_song_item)

        loading_song_content_row: ft.Row = loading_song_item.content

        loaded_song_info = ft.Column(
            [
                ft.Text(artist_name), ft.Text(album_name), ft.Text(song_name), ft.Text(f"{genres}")
            ]
        )

        loading_song_content_row.controls[-1] = loaded_song_info

        loading_song_item.update()

        self.loading_song_items[song_id] = loading_song_item

    def add_song_cover_art(
            self,
            song_id: int,
            b64_image_bytes: str
    ):
        song_item: ft.Container = self.loading_song_items[song_id]
        loading_song_content_row: ft.Row = song_item.content

        image = ft.Container(
            ft.Image(
                src_base64=b64_image_bytes,
                fit=ft.ImageFit.FILL
            ),
            height=150,
            width=120,
            bgcolor=ft.Colors.GREY
        )

        loading_song_content_row.controls[0] = image

        song_item.update()

        del self.loading_song_items[song_id]

    def _load_song_previews(self, *args):
        query = self.song_search.value

        self.transport.write(
            ClientMessage(
                authentication=self.user_cache.session_token,
                method="GET",
                endpoint="song/download/preview",
                payload={
                    "query": query
                }
            ).encode()
        )

    def _automatically_load_more(self, e: ft.OnScrollEvent):
        current_scroll_direction = e.direction

        if current_scroll_direction:
            self.last_scroll_direction = current_scroll_direction

        if e.pixels == e.max_scroll_extent and self.last_scroll_direction == "reverse":
            self.last_scroll_direction = None

            self._load_song_previews()

    def _initialize_gridview(self):
        self.last_scroll_direction: str = ""
        self.test = 0

        self.song_item_gridview: ft.GridView = ft.GridView(
            runs_count=1,
            max_extent=250,
            child_aspect_ratio=1.0,
            spacing=5,
            run_spacing=5,
            padding=10,
        )
        self.load_more_button: ft.Container = ft.Container(
            height=50,
            bgcolor=ft.Colors.RED,
            on_click=self._load_song_previews,
        )

        self.song_item_listview: ft.ListView = ft.ListView(
            controls=[
                self.song_item_gridview,
                self.load_more_button
            ],
            expand=True,
            on_scroll=self._automatically_load_more,
        )

    def  _initialize_search_bar(self):
        self.song_search: ft.TextField = ft.TextField(

        )

    def _initialize_controls(self):
        self._initialize_gridview()
        self._initialize_search_bar()

        self.page_view = ft.Row(
            [
                self.sidebar,
                ft.Container(
                    expand=7,
                    content=ft.Column(
                        [
                            ft.Container(
                                expand=True,
                                content=ft.Column(
                                    expand=True,
                                    controls=[
                                        ft.Container(height=50, expand_loose=True, bgcolor=ft.Colors.RED, content=self.song_search),
                                        self.song_item_listview,
                                        ft.Container(height=50, expand_loose=True, bgcolor=ft.Colors.RED),
                                    ]
                                )
                            )
                        ],
                        expand=True,
                    ),
                ),
            ],
            expand=10,
        )

    def append_error(self, error_control: ft.Control):
        current_last_control_data = self.page_view.controls[-1].data

        if isinstance(current_last_control_data, dict) \
                and isinstance(error_control.data, dict) \
                and current_last_control_data.get("error_type") == error_control.data.get("error_type"):
            # removes the current last control if it is also an error message, this is done so that error messages
            # don't stack
            self.page_view.controls.pop()

        self.page_view.controls.append(error_control)

        self.page_view.update()

    def show(self, clear: bool = True):
        """:param clear: whether to clear the page before trying to add the page's content or not."""

        if clear:
            self.page.clean()

        self.page.view = self
        self.page.add(self.page_view)

        self.page.update()


def main(page: ft.Page):
    HomePage(page=page).show()


if __name__ == "__main__":
    ft.app(main, assets_dir="Assets")
