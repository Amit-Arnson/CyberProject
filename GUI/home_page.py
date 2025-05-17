import flet as ft

from encryptions import EncryptedTransport
from Caches.user_cache import ClientSideUserCache

from GUI.Controls.navigation_sidebar import NavigationSidebar
from GUI.Controls.song_view import SongView

from pseudo_http_protocol import ClientMessage

import hashlib


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

        self.loading_song_items: dict[str, ft.Container] = {}

        self.loaded_song_ids: list[int] = []
        """
            this list is the "exclude" list.
            this list is limited to 100 items, and is First In First Out (see self._add_excluded_song_id)
        """

        self.loaded_genre_names: list[str] = []
        """
            this is purely used for tracking the "browse" tab. it tracks which genres the server has already sent in order
            to be able to add them to an excluded list
        """

        self.current_filters: dict[str, ...] = {}
        """
        dict[
            "genres": list[genre name],
            "artist": list[artist name],
            "duration": {
                "minimum": integer duration in milliseconds,
                "maximum": integer duration in milliseconds
            }
            
            #--- not implemented yet ---#
            -- in bpm
            "tempo": {"minimum": int, "maximum": int},
            -- between 1 and 5 (stars)
            "rating": {"minimum": int, "maximum": int}
        ]
        """

        self.preview_image_value_dict: dict[str, ...] = {
            "expand": True,
            "expand_loose": True,
            "border_radius": 7
        }

        self.gridview_extent = 320

        self.song_view_popup: SongView | None = None
        self.is_viewing_song = False
        """
            this is a check in order to see if the user is currently viewing a song using the SongView, this is important
            for the audio file chunk buffering.
        """

        self.navigate_data = {}
        """the data that the current navigate tab is on, this is used for the "load more" button"""

        self.page.recently_viewed_songs = []
        """the list of the recently viewed song IDs, saved to page as to be persistent per-run instead of per-page"""

        self._initialize_controls()

    def _create_loading_item(
            self,
            song_id: int,
            file_id: str,
            artist_name: str,
            album_name: str,
            song_name: str,
            song_length: int,  # milliseconds
            genres: list[str]
    ) -> ft.Container:
        song_cover_art_loading = ft.Container(
            **self.preview_image_value_dict,
            bgcolor=ft.Colors.GREY,
            content=ft.Container(
                width=20,
                height=20,
                content=ft.ProgressRing(
                    color=ft.Colors.GREY_300,
                    stroke_width=2,
                )
            ),
            alignment=ft.Alignment(0, 0)
        )

        off_hover_stack_gradient = ft.LinearGradient(
            colors=[
                ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
                ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                ft.Colors.with_opacity(0.025, ft.Colors.BLACK),
                ft.Colors.with_opacity(0, ft.Colors.BLACK),
                ft.Colors.with_opacity(0.025, ft.Colors.BLACK),
                ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
            ],
            begin=ft.alignment.top_center,
            end=ft.alignment.bottom_center,
        )

        on_hover_stack_gradient = ft.LinearGradient(
            colors=[
                ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
                ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
                ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
                ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
            ],
            begin=ft.alignment.top_center,
            end=ft.alignment.bottom_center,
        )

        stack_gradient = ft.Container(
            expand=True,
            bgcolor=ft.Colors.GREEN,
            gradient=off_hover_stack_gradient
        )

        song_item_load: ft.Container = ft.Container(
            width=200,
            height=200,
            border_radius=5,
            bgcolor=ft.Colors.GREY_200,
            content=ft.Stack(
                [
                    # background
                    song_cover_art_loading,

                    stack_gradient,

                    # top column (artist/song/album name)
                    ft.Column(),

                    # bottom column (genres/length)
                    ft.Column(),
                ],
                data={
                    # used in the on_hover
                    "off_hover_gradient": off_hover_stack_gradient,
                    "on_hover_gradient": on_hover_stack_gradient,
                    "gradient": stack_gradient,

                    # used in the check when streaming cover art image bytes
                    "has_loaded_initial_cover_bytes": False,
                }
            ),
            data={
                "cover_art": song_cover_art_loading,
                "song_id": song_id,
                "file_id": file_id,
                "artist_name": artist_name,
                "album_name": album_name,
                "song_name": song_name,
                "song_length": song_length,
                "genres": genres
            },
            on_click=self._open_song_view
        )

        return song_item_load

    def _open_song_view(self, event: ft.ControlEvent):
        song_item = event.control

        song_data: dict[str, str | int | list[str]] = song_item.data
        song_id = song_data["song_id"]

        self.page.recently_viewed_songs: list[int]

        if len(self.page.recently_viewed_songs) > 100:
            self.page.recently_viewed_songs.pop(0)

        if song_id not in self.page.recently_viewed_songs:
            self.page.recently_viewed_songs.append(song_id)

        loading_song_content_stack: ft.Stack = song_item.content

        image_container: ft.Container = loading_song_content_stack.controls[0]
        image: ft.Image = image_container.content

        song_view = SongView(
            transport=self.transport,
            user_cache=self.user_cache,
            cover_art_b64=image.src_base64,
            song_id=song_data["song_id"],
            artist_name=song_data["artist_name"],
            album_name=song_data["album_name"],
            song_name=song_data["song_name"],
            song_length=song_data["song_length"],
            genres=song_data["genres"],
            open=True,
        )

        self.is_viewing_song = True

        self.page_view.controls.append(song_view)

        self.song_view_popup = song_view

        self.page_view.update()

    def _add_song_item(self, item: ft.Container):
        self.song_item_gridview.controls.append(item)

        self.song_item_gridview.update()

    def _add_excluded_song_id(self, song_id: int):
        if len(self.loaded_song_ids) >= 100:
            self.loaded_song_ids.pop(0)

        self.loaded_song_ids.append(song_id)

    @staticmethod
    def _song_item_hover(event: ft.ControlEvent):
        song_item_stack: ft.Stack = event.control.data

        is_hovering = event.data == "true"

        if is_hovering:
            gradient = song_item_stack.data["on_hover_gradient"]
        else:
            gradient = song_item_stack.data["off_hover_gradient"]

        gradient_container: ft.Container = song_item_stack.controls[2]
        gradient_container.gradient = gradient

        gradient_container.update()

    def add_song_info(
            self,
            song_id: int,
            file_id: str,
            artist_name: str,
            album_name: str,
            song_name: str,
            song_length: int,
            genres: list[str],
    ):
        loading_song_item: ft.Container = self._create_loading_item(
            song_id=song_id,
            file_id=file_id,
            artist_name=artist_name,
            album_name=album_name,
            song_name=song_name,
            song_length=song_length,
            genres=genres
        )
        self._add_song_item(loading_song_item)

        # add the song ID to the loaded songs list, so that the client can request to exclude it when searching/loading
        # more songs
        self._add_excluded_song_id(song_id)

        loading_song_content_stack: ft.Stack = loading_song_item.content

        genre_span = ft.Text(
            spans=[ft.TextSpan(f"{genre}{', ' if i < len(genres) - 1 else ''}") for i, genre in enumerate(genres)],
            size=12,
            color=ft.Colors.with_opacity(0.8, ft.Colors.GREY_50),
            weight=ft.FontWeight.W_500,
        )

        max_text_size = 20

        sub_text_info_values = {
            "size": max_text_size - 6,
            "color": ft.Colors.WHITE,
            "weight": ft.FontWeight.W_500,
        }

        # top column
        song_info_column = ft.Column(
            [
                ft.Text(song_name, size=max_text_size, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),

                ft.Row(
                    [
                        ft.Text(album_name, **sub_text_info_values),
                        ft.Text("•", **sub_text_info_values),
                        ft.Text(artist_name, **sub_text_info_values)
                    ],
                    spacing=3,
                    wrap=True
                )
            ],
            spacing=0,
            expand_loose=True,
            expand=True,
        )

        top_row = ft.Row(
            [
                song_info_column,
                ft.Container(
                    ft.Icon(
                        ft.Icons.STAR_ROUNDED,
                        color=ft.Colors.WHITE,
                        size=30
                    ),
                    padding=5,

                    # todo: implement this
                    # this should only be visible when hovering. i need to check how i want to implement the on_hover
                    visible=False
                )
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

        loading_song_content_stack.controls[-2] = ft.Container(
            top_row,
            padding=5,
        )

        loading_song_content_stack.controls[-1] = ft.Container(
            genre_span,
            padding=5,
            bottom=0,
            height=100,
            width=self.gridview_extent - 20,
            alignment=ft.Alignment(-1, 1),
        )

        # an invisible container that is placed on top that is used to add all of the on_... events to the stack
        event_container = ft.Container(
            expand=True,
            data=loading_song_content_stack,
            on_hover=self._song_item_hover,
        )

        loading_song_content_stack.controls.append(event_container)

        loading_song_item.update()

        self.loading_song_items[file_id] = loading_song_item

    def stream_cover_art_chunks(self, file_id: str, song_id: int, b64_chunk: str, is_last_chunk: bool = False):
        song_item: ft.Container = self.loading_song_items[file_id]
        loading_song_content_stack: ft.Stack = song_item.content

        if not loading_song_content_stack.data["has_loaded_initial_cover_bytes"]:
            image_container = ft.Container(
                ft.Image(
                    src_base64=b64_chunk,
                    fit=ft.ImageFit.FILL,
                    # images below a certain resolution did not fully cover the container when using ImageFit, so i set
                    # a manual width and height that will be equal to what the gridview allows and thus will always fit
                    width=self.gridview_extent,
                    height=self.gridview_extent,
                ),
                **self.preview_image_value_dict,
            )

            loading_song_content_stack.controls[0] = image_container
            loading_song_content_stack.data["has_loaded_initial_cover_bytes"] = True
        else:
            image_container: ft.Container = loading_song_content_stack.controls[0]
            image: ft.Image = image_container.content

            image.src_base64 += b64_chunk

        song_item.update()

        if is_last_chunk:
            del self.loading_song_items[file_id]

    async def stream_audio_chunks(self, file_id: str, song_id: int, b64_chunk: str, is_last_chunk: bool = False):
        if self.song_view_popup:
            await self.song_view_popup.stream_audio_chunks(
                file_id=file_id,
                song_id=song_id,
                b64_chunk=b64_chunk,
                is_last_chunk=is_last_chunk
            )

    async def stream_sheet_chunks(self, file_id: str, song_id: int, b64_chunk: str, is_last_chunk: bool = False):
        if self.song_view_popup:
            await self.song_view_popup.stream_sheet_chunks(
                file_id=file_id,
                song_id=song_id,
                b64_chunk=b64_chunk,
                is_last_chunk=is_last_chunk
            )

    async def add_song_comments(self, comments: list[dict], ai_summary: str):
        if self.song_view_popup:
            await self.song_view_popup.add_comments(
                comments=comments,
                ai_summary=ai_summary
            )

    @staticmethod
    def _string_to_hex_color(string: str) -> str:
        hash_bytes = hashlib.sha256(string.encode()).digest()
        r, g, b = hash_bytes[0], hash_bytes[1], hash_bytes[2]
        return f'#{r:02x}{g:02x}{b:02x}'  # HEX color string

    async def add_genres_browse(self, genres: list[str]):
        for genre in genres:
            if len(self.loaded_genre_names) > 100:
                self.loaded_genre_names.pop(0)

            self.loaded_genre_names.append(genre)

            genre_container = ft.Container(
                content=ft.Text(genre, size=30, weight=ft.FontWeight.W_500),
                bgcolor=self._string_to_hex_color(genre),
                alignment=ft.Alignment(0, 0),
                border_radius=10,
                on_click=self._navigate,
                data={
                    "endpoint": "song/genres/download/preview",
                    "payload": {
                        "exclude": self.loaded_song_ids,
                        "limit": 10,
                        "genre": genre
                    }
                }
            )

            self.song_item_gridview.controls.append(genre_container)

        self.song_item_gridview.update()

    def _load_song_previews(self, *args):
        if not self.transport:
            return

        query = self.song_search.value

        print(self.navigate_data)

        endpoint = self.navigate_data.get("endpoint", "song/download/preview")
        payload = self.navigate_data.get(
            "payload",
            {
                "query": query,
                "exclude": self.loaded_song_ids,
                "limit": 10,
                # filters is a required parameter, but it can be an empty dict to indicate none
                "filters": self.current_filters
            }
        )

        self.transport.write(
            ClientMessage(
                authentication=self.user_cache.session_token,
                method="GET",
                endpoint=endpoint,
                payload=payload
            ).encode()
        )

    def _automatically_load_more(self, e: ft.OnScrollEvent):
        current_scroll_direction = e.direction

        if current_scroll_direction:
            self.last_scroll_direction = current_scroll_direction

        if e.pixels == e.max_scroll_extent and self.last_scroll_direction == "reverse":
            self.last_scroll_direction = None

            self._load_song_previews()

    def _clear_screen(self, update: bool = True):
        for tab in self.tab_list:
            tab: ft.Container

            # reset all the tabs to be the default BLUE color, so that it removes the color of the selected tab (to
            # allow for a new selection)
            tab.bgcolor = ft.Colors.BLUE

        self.song_item_gridview.controls.clear()
        self.loaded_song_ids.clear()

        if update:
            self.page.update()

    def _initialize_gridview(self):
        self.last_scroll_direction: str = ""
        self.test = 0

        self.song_item_gridview: ft.GridView = ft.GridView(
            runs_count=1,
            max_extent=self.gridview_extent,
            child_aspect_ratio=1.0,
            spacing=5,
            run_spacing=5,
            padding=10,
        )

        self.load_more_button: ft.Container = ft.Container(
            content=ft.Text("load more", weight=ft.FontWeight.W_500, color=ft.Colors.WHITE),
            height=50,
            bgcolor=ft.Colors.BLUE_800,
            border_radius=10,
            alignment=ft.Alignment(0, 0),
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

    def _search(self, event):
        print(event)

        self._clear_screen(update=True)

        # send the server the search request
        self._load_song_previews()

    def _initialize_search_bar(self):
        self.song_search: ft.TextField = ft.TextField(
            border_width=0,
            border_radius=90,
            color=ft.Colors.WHITE,
            cursor_color=ft.Colors.WHITE70,
            on_submit=self._search,
            expand=True
        )

        self.search_bar: ft.Container = ft.Container(
            bgcolor=ft.Colors.BLUE,
            border_radius=90,
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.SEARCH_ROUNDED,
                        color=ft.Colors.WHITE
                    ),
                    self.song_search
                ],
            ),
            expand_loose=True,
            expand=True,
            padding=ft.Padding(
                right=10,
                left=10,
                top=0,
                bottom=0
            )
        )

        self.advanced_search: ft.Container = ft.Container(
            width=50,
            height=50,
            bgcolor=ft.Colors.BLUE,
            border_radius=10
        )

        self.advanced_search_bar: ft.Container = ft.Container(
            ft.Row(
                [
                    self.advanced_search,
                    self.search_bar
                ]
            ),
            padding=5
        )

    @staticmethod
    def _highlight_tab(event: ft.ControlEvent):
        tab_container: ft.Container = event.control

        is_currently_hovering = event.data

        if is_currently_hovering == "true":
            tab_container.bgcolor = ft.Colors.BLUE_400
        else:
            tab_container.bgcolor = tab_container.data["color"]

        tab_container.update()

    def _navigate(self, event):
        self._clear_screen(update=True)

        self.loaded_song_ids.clear()
        self.loaded_genre_names.clear()

        self.navigate_data = event.control.data
        self._load_song_previews()

    def _initialize_navigation_tabs(self):
        nav_tab_dict: dict[str, ...] = {
            "bgcolor": ft.Colors.BLUE,
            "border_radius": 1,
            "expand": True,
            "padding": 10,
            "on_hover": self._highlight_tab,
            "on_click": self._navigate
        }

        self.home_tab: ft.Container = ft.Container(
            **nav_tab_dict,
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.HOME_ROUNDED,
                        color=ft.Colors.BLUE_50
                    ),
                    ft.Text(
                        "home",
                        color=ft.Colors.BLUE_50,
                        weight=ft.FontWeight.W_500
                    )
                ]
            ),
            data={
                "color": ft.Colors.BLUE,
            }
        )

        self.browse: ft.Container = ft.Container(
            **nav_tab_dict,
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.LIBRARY_MUSIC_ROUNDED,
                        color=ft.Colors.WHITE
                    ),
                    ft.Text(
                        "browse",
                        color=ft.Colors.WHITE,
                        weight=ft.FontWeight.W_500
                    )
                ]
            ),
            data={
                "color": ft.Colors.BLUE,
                "endpoint": "song/genres",  # -> list[genres]
                "payload": {
                    "exclude": self.loaded_genre_names,
                }
            }
        )

        self.favorites: ft.Container = ft.Container(
            **nav_tab_dict,
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.STAR_ROUNDED,
                        color=ft.Colors.WHITE
                    ),
                    ft.Text(
                        "favorites",
                        color=ft.Colors.WHITE,
                        weight=ft.FontWeight.W_500
                    )
                ]
            ),
            data={
                "color": ft.Colors.BLUE,
                "endpoint": "song/favorites/download/preview"
            }
        )

        self.recommended: ft.Container = ft.Container(
            **nav_tab_dict,
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.FAVORITE,
                        color=ft.Colors.WHITE
                    ),
                    ft.Text(
                        "recommended",
                        color=ft.Colors.WHITE,
                        weight=ft.FontWeight.W_500
                    )
                ]
            ),
            data={
                "color": ft.Colors.BLUE,
                "endpoint": "song/recommended/download/preview",
                "payload": {
                    "exclude": self.loaded_song_ids,
                    "limit": 10
                }
            }
        )

        self.recent: ft.Container = ft.Container(
            **nav_tab_dict,
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.REPLAY_ROUNDED,
                        color=ft.Colors.WHITE
                    ),
                    ft.Text(
                        "recent",
                        color=ft.Colors.WHITE,
                        weight=ft.FontWeight.W_500
                    )
                ]
            ),
            data={
                "color": ft.Colors.BLUE,
                "endpoint": "song/recent/download/preview",
                "payload": {
                    "include": self.page.recently_viewed_songs,
                    "exclude": self.loaded_song_ids,
                    "limit": 10
                }
            }
        )

        self.your_uploads: ft.Container = ft.Container(
            **nav_tab_dict,
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.MUSIC_NOTE_ROUNDED,
                        color=ft.Colors.WHITE
                    ),
                    ft.Container(
                        content=ft.Text(
                            "uploads",
                            color=ft.Colors.WHITE,
                            weight=ft.FontWeight.W_500,
                        ),
                    )
                ],
            ),
            data={
                "color": ft.Colors.BLUE,
                "endpoint": "song/uploads/download/preview",
                "payload": {
                    "exclude": self.loaded_song_ids,
                    "limit": 10
                }
            }
        )

        self.tab_list = [
            self.home_tab,
            self.browse,
            self.favorites,
            self.recommended,
            self.recent,
            self.your_uploads
        ]

        self.navigation_row: ft.Container = ft.Container(
            content=ft.Row(
                spacing=2,
                controls=self.tab_list,
            ),
        )

    def _initialize_controls(self):
        self._initialize_gridview()
        self._initialize_search_bar()
        self._initialize_navigation_tabs()

        self.page_view = ft.Row(
            [
                self.sidebar,
                ft.Container(
                    expand=8,
                    padding=ft.Padding(
                        top=10, bottom=10, right=20, left=20
                    ),
                    content=ft.Column(
                        [
                            ft.Container(
                                expand=True,
                                content=ft.Column(
                                    expand=True,
                                    controls=[
                                        ft.Container(
                                            expand_loose=True,
                                            bgcolor=ft.Colors.BLUE_800,
                                            content=ft.Column(
                                                [
                                                    self.advanced_search_bar,
                                                    self.navigation_row
                                                ],
                                            ),
                                            border_radius=5,
                                            padding=2,
                                        ),
                                        ft.Container(
                                            content=self.song_item_listview,
                                            expand=True,
                                            padding=10,
                                        ),
                                        ft.Container(
                                            height=50,
                                            expand_loose=True,
                                            bgcolor=ft.Colors.BLUE_800,
                                            border_radius=5,
                                        ),
                                    ],
                                )
                            )
                        ],
                        expand=True,
                    ),
                ),
            ],
            expand=10,
            spacing=0,
        )

        # automatically try to load the default song previews (which would be what the server recommends)
        self._load_song_previews()

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
