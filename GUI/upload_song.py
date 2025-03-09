import flet as ft

from encryptions import EncryptedTransport

from GUI.Controls.navigation_sidebar import NavigationSidebar
from GUI.Controls.tag_input import TagInput

from Caches.user_cache import ClientSideUserCache

from Utils.chunk import send_chunk
import aiofiles


class UploadPage:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.LIGHT

        # these sizes are the optimal ratio for the average PC screen
        self.page_width = 1280
        self.page_height = 720

        self.selected_song_path: str = ""
        self.selected_sheet_paths: list[str] = []

        self.transport: EncryptedTransport | None = None
        if hasattr(page, "transport"):
            self.transport: EncryptedTransport = page.transport

        # this holds the session token (which is the authentication)
        self.user_cache: ClientSideUserCache | None = None
        if hasattr(page, "user_cache"):
            self.user_cache: ClientSideUserCache = page.user_cache

        self.audio_file_path: str = ""
        self.thumbnail_file_path: str = ""

        self.sheet_image_container_id = 0
        self.sheet_file_paths: dict[int, str] = {}

        self.sidebar = NavigationSidebar(page=page)

        # we define 2 different file pickers so that we can point the on_result to different functions in order to make
        # sorting between images and audio files easier
        self.sound_file_picker = ft.FilePicker()
        self.sound_file_picker.on_result = self._on_finish_sound_select

        self.image_file_picker = ft.FilePicker()
        self.image_file_picker.on_result = self._on_finish_image_select

        # add the file picker control to the page
        self.page.overlay.append(self.sound_file_picker)
        self.page.overlay.append(self.image_file_picker)

        self._initialize_controls()

    def _initialize_sidebar_top(self):
        self.sidebar.top_part.margin = ft.Margin(top=10, bottom=0, right=0, left=0)

        # override the on_click method so that clicking on the button does not reset the information already input
        self.sidebar.goto_upload_song.on_click = lambda _: _

        self.sidebar.top_part.content = ft.Container(
            expand=True,
            height=75,
            bgcolor=ft.Colors.BLUE_900,
            content=ft.Text(
                "Upload Song", size=25, color=ft.Colors.BLUE_700,
                weight=ft.FontWeight.BOLD
            ),
            alignment=ft.Alignment(0, 0)
        )

        # the sidebar is set to 2 and the right side of the page is set to 10. this means the sidebar takes 20% of the available screen
        self.sidebar.expand = 2

    def _select_sound_files(self, e: ft.ControlEvent):
        self.sound_file_picker.pick_files(
            allow_multiple=False,
            file_type=ft.FilePickerFileType.AUDIO
        )

    def _select_image_files(self, e: ft.ControlEvent):
        self.image_file_picker.pick_files(
            allow_multiple=True,
            file_type=ft.FilePickerFileType.IMAGE
        )

    async def _on_finish_sound_select(self, e: ft.FilePickerResultEvent):
        selected_files = e.files

        if not selected_files:
            return

        session_token: str = self.user_cache.session_token
        print(f"session token: {session_token}")

        audio_file = selected_files[0]
        file_path: str = audio_file.path

        try:
            async with aiofiles.open(file_path, "rb") as file:
                file_bytes = await file.read()
        except Exception as e:
            print(e)

        await send_chunk(
            transport=self.transport,
            session_token=session_token,
            tags=["one", "two"],
            artist_name="a",
            album_name="b",
            song_name="c",
            song_path=file_path,
        )

        print(audio_file)
        print(type(audio_file))
        print(e.files)
        print("selected audio")

    def _on_finish_image_select(self, e: ft.FilePickerResultEvent):
        print(e.files)
        print("selected image")

        selected_files = e.files

        if not selected_files:
            return

        # session_token: str = self.user_cache.session_token
        # print(f"session token: {session_token}")

        file_paths: list[str] = [file.path for file in selected_files]
        file_names: list[str] = [file.name for file in selected_files]

        self._add_music_sheets_to_row(file_paths, file_names)

    def _remove_sheet_image(self, event: ft.ControlEvent):
        image_container = event.control
        image_unique_id: int = image_container.data

        # removes the container from the sheet row
        self.sheet_selector_row.controls.remove(image_container)

        # removes the path from the dictionary, along with its ID key
        del self.sheet_file_paths[image_unique_id]

        self.sheet_selector_row.update()

    @staticmethod
    def _hover_sheet_image(event: ft.ControlEvent):
        image_container = event.control

        if event.data == "true":
            image: ft.Image = image_container.content

            image_name: str = image.data

            image_remove_overlay: ft.Stack = ft.Stack(
                controls=[
                    ft.Container(
                        content=image,
                        width=image_container.width,
                        height=image_container.height,
                    ),
                    ft.Container(
                        gradient=ft.LinearGradient(
                            colors=[
                                ft.Colors.with_opacity(0.4, ft.Colors.BLACK),
                                ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                                ft.Colors.with_opacity(0.1, ft.Colors.BLACK),
                                ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                                ft.Colors.with_opacity(0.4, ft.Colors.BLACK),
                            ],
                            begin=ft.alignment.top_center,
                            end=ft.alignment.bottom_center
                        ),
                        width=image_container.width,
                        height=image_container.height,
                        padding=5,
                    ),
                    ft.Container(
                        content=ft.Container(
                            content=ft.Icon(
                                ft.Icons.CLOSE,
                                color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE),
                            ),
                            #padding=5,
                            width=image_container.width / 5,
                            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.GREY),
                            border_radius=180,
                            expand_loose=True,
                            alignment=ft.Alignment(0, 0),
                        ),
                        padding=5,
                        height=40,
                        top=0,
                        left=0
                    ),
                    ft.Container(
                        content=ft.Container(
                            content=ft.Text(
                                f"{image_name}",
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE),
                                overflow=ft.TextOverflow.ELLIPSIS
                            ),
                            padding=5,
                            width=image_container.width - 10,
                            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.GREY),
                            border_radius=10,
                            expand_loose=True,
                            alignment=ft.Alignment(0, 0),
                        ),
                        padding=5,
                        height=40,
                        bottom=0,
                    ),
                ],
            )

            image_container.content = image_remove_overlay
        else:
            image_remove_overlay: ft.Stack = image_container.content

            image: ft.Image = image_remove_overlay.controls[0].content

            image_container.content = image

        image_container.update()

    def _add_music_sheets_to_row(self, image_paths: list[str], image_names: list[str]):
        image_containers: list[ft.Container] = []

        for path, name in zip(image_paths, image_names):
            current_id = self.sheet_image_container_id

            image_container = ft.Container(
                width=150,
                height=190,
                content=ft.Image(
                    src=path,
                    fit=ft.ImageFit.FILL,
                    data=name
                ),
                border_radius=3,
                data=current_id,
                on_click=self._remove_sheet_image,
                on_hover=self._hover_sheet_image,
            )

            # to be able to easily remove it later (when clicking on the image container), i made the saved paths into
            # a dictionary with a unique ID (since the ID number increments every time, it will never be the same number)
            self.sheet_file_paths[current_id] = path

            self.sheet_image_container_id += 1

            image_containers.append(image_container)

        # i pop the current last item (which will always be the file selector), then append it to the end.
        # this is done so that you dont need to scroll in order to get to the file selector
        sheet_selector: ft.Container = self.sheet_selector_row.controls.pop()

        image_containers.append(sheet_selector)

        self.sheet_selector_row.controls.extend(image_containers)

        self.sheet_selector_row.update()

    def _initialize_file_selectors(self):
        self.song_selector = ft.Container(
            on_click=self._select_sound_files,
            expand=True,
            expand_loose=True,
            height=150,
            bgcolor=ft.Colors.RED
        )

        self.sheet_selector = ft.Container(
            on_click=self._select_image_files,
            width=150,
            height=190,
            content=ft.Icon(ft.Icons.ADD, color=ft.Colors.GREY_800),
            alignment=ft.Alignment(0, 0),
            border=ft.border.all(1, ft.Colors.GREY_800),
            border_radius=3,
            ink=True,
            ink_color=ft.Colors.GREY
        )

        self.sheet_selector_row: ft.Row = ft.Row(
            [
                self.sheet_selector
            ],
            auto_scroll=True,
            scroll=ft.ScrollMode.AUTO,
        )

    def _initialize_song_info_textbox(self):
        self.song_name_textbox = ft.TextField(
            label="song name",
            expand=True,
        )

        self.song_album_textbox = ft.TextField(
            label="song album",
            expand=True,
        )

        self.song_artist_textbox = ft.TextField(
            label="song band",
            expand=True,
        )

        self.song_info_row: ft.Row = ft.Row(
            [
                self.song_name_textbox, self.song_album_textbox, self.song_artist_textbox
            ],
        )

    def _initialize_genre_tag_textbox(self):
        self.selected_genres_textbox = TagInput(
            border_radius=5,
            border=ft.border.all(color=ft.Colors.BLACK),
            padding=ft.Padding(
                right=0, top=2, bottom=2, left=2
            ),
            tag_spacing=5,
            hint_text="add genre",
            hint_text_padding=1
        )

    def _initialize_description_textbox(self):
        self.description_textbox = ft.TextField(
            label="description",
        )

    def _initialize_controls(self):
        self._initialize_sidebar_top()

        self._initialize_file_selectors()
        self._initialize_song_info_textbox()
        self._initialize_description_textbox()
        self._initialize_genre_tag_textbox()

        # this is just a temporary container so that something takes that space up
        aa = ft.Container(
            padding=10,
            expand=8,
            content=ft.Column(
                [
                    self.song_selector,

                    ft.Divider(),

                    self.song_info_row,
                    # self.description_textbox,
                    self.selected_genres_textbox,

                    ft.Divider(),

                    ft.Text("Add Music Sheets", weight=ft.FontWeight.BOLD),
                    self.sheet_selector_row,

                    ft.Divider(),

                ],
                expand=True,
                scroll=ft.ScrollMode.ALWAYS,
                auto_scroll=True
            ),
            alignment=ft.Alignment(-1, -1)
        )

        self.page_view = ft.Row(
            [
                self.sidebar,
                aa,
            ],
            spacing=0,
            expand=True
        )

    def show(self, clear: bool = True):
        """:param clear: whether to clear the page before trying to add the page's content or not."""

        if clear:
            self.page.clean()

        self.page.view = self
        self.page.add(self.page_view)

        self.page.update()


def main(page: ft.Page):
    UploadPage(page=page).show()


if __name__ == "__main__":
    ft.app(main, assets_dir="Assets")
