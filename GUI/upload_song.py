import flet as ft

from encryptions import EncryptedTransport

from GUI.Controls.navigation_sidebar import NavigationSidebar
from GUI.Controls.tag_input import TagInput

from Caches.user_cache import ClientSideUserCache

from Utils.chunk import send_chunk
import aiofiles


# This section was moved to a class due to being hard to read when inside of a function
class ImageRemoveHover(ft.Stack):
    def __init__(self, image: ft.Image, image_name: str, width: int, height: int):
        super().__init__()

        self.image = image
        self.image_name = image_name
        self.width = width
        self.height = height

        # Define controls using helper methods for better organization
        self.controls = [
            self._create_image_container(),
            self._create_gradient_overlay(),
            self._create_close_icon_overlay(),
            self._create_text_overlay(),
        ]

    def _create_image_container(self) -> ft.Container:
        """Creates the container for the image."""
        return ft.Container(
            content=self.image,
            width=self.width,
            height=self.height,
        )

    def _create_gradient_overlay(self) -> ft.Container:
        """Creates the gradient overlay container."""
        return ft.Container(
            gradient=ft.LinearGradient(
                colors=[
                    ft.Colors.with_opacity(0.4, ft.Colors.BLACK),
                    ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                    ft.Colors.with_opacity(0.1, ft.Colors.BLACK),
                    ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                    ft.Colors.with_opacity(0.4, ft.Colors.BLACK),
                ],
                begin=ft.alignment.top_center,
                end=ft.alignment.bottom_center,
            ),
            width=self.width,
            height=self.height,
            padding=5,
        )

    def _create_close_icon_overlay(self) -> ft.Container:
        """Creates the close icon overlay container."""
        return ft.Container(
            content=ft.Container(
                content=ft.Icon(
                    ft.Icons.CLOSE,
                    color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE),
                ),
                width=self.width / 5,
                bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.GREY),
                border_radius=180,
                expand_loose=True,
                alignment=ft.Alignment(0, 0),
            ),
            padding=5,
            height=40,
            top=0,
            left=0,
        )

    def _create_text_overlay(self) -> ft.Container:
        """Creates the text overlay container."""
        return ft.Container(
            content=ft.Container(
                content=ft.Text(
                    self.image_name,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE),
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                padding=5,
                width=self.width - 10,
                bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.GREY),
                border_radius=10,
                expand_loose=True,
                alignment=ft.Alignment(0, 0),
            ),
            padding=5,
            height=40,
            bottom=0,
        )


class UploadCoverArtDefault(ft.Stack):
    def __init__(self):
        super().__init__()

        # Default size values for containers
        self.default_size_values: dict[str, int] = {
            "width": 25,
            "height": 25,
        }

        # Default border styling
        self.default_border_value = ft.BorderSide(
            color=ft.Colors.GREY_700, width=2
        )

        # Define controls for upload cover art
        self.controls = [
            self._create_main_text_container(),
            self._create_corner_container(bottom=0, right=0, add_sides=["right", "bottom"]),
            self._create_corner_container(bottom=0, left=0, add_sides=["left", "bottom"]),
            self._create_corner_container(top=0, right=0, add_sides=["right", "top"]),
            self._create_corner_container(top=0, left=0, add_sides=["left", "top"]),
        ]

    def _create_main_text_container(self) -> ft.Container:
        """Creates the main text container."""
        return ft.Container(
            content=ft.Text(
                spans=[
                    ft.TextSpan("ADD\n"),
                    ft.TextSpan("COVER"),
                ],
                text_align=ft.TextAlign.CENTER,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.GREY_500,
            ),
            height=150,
            width=120,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.GREY_500),
            alignment=ft.Alignment(0, 0),
        )

    def _create_corner_container(self, **kwargs) -> ft.Container:
        """
        Creates a corner container with specified positioning and border sides.

        :param kwargs: Positioning arguments (e.g., top, bottom, left, right).
        :param add_sides: List of sides for which borders are added.
        """
        add_sides = kwargs.pop("add_sides", [])
        border_kwargs = {
            side: self.default_border_value for side in add_sides
        }

        return ft.Container(
            **self.default_size_values,
            border=ft.Border(**border_kwargs),
            **kwargs,
        )


class UploadPage:
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

        self.sheet_image_container_id = 0

        # this is the ID-path dict for image sheet paths, so you need to use the .values() to get the paths themselves
        self.sheet_file_paths: dict[int, str] = {}
        self.selected_song_path: str = ""
        self.selected_cover_art_path: str = ""

        self.upload_cover_art_default_content: ft.Stack = UploadCoverArtDefault()

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
        # override the on_click method so that clicking on the button does not reset the information already input
        self.sidebar.goto_upload_song.on_click = None

        # the sidebar is set to 2 and the right side of the page is set to 10. this means the sidebar takes 20% of the available screen
        self.sidebar.expand = 2

    # todo: make it cancel the "upload" task when an error regarding invalid request ID is given (which can be checked with the error's "extras")
    async def _upload_all_files(self, *args):
        session_token: str = self.user_cache.session_token
        print(f"session token: {session_token}")

        image_paths: list[str] = list(self.sheet_file_paths.values())
        audio_path: str = self.selected_song_path

        tags = self.selected_genres_textbox.get_values()
        artist_name = self.song_artist_textbox.value
        album_name = self.song_album_textbox.value
        song_name = self.song_name_textbox.value

        self._add_blocking_overlay()

        print(f"song path: {audio_path}")

        await send_chunk(
            transport=self.transport,
            session_token=session_token,
            tags=tags,
            artist_name=artist_name,
            album_name=album_name,
            song_name=song_name,
            song_path=audio_path,
            image_path_list=image_paths
        )

        self._remove_blocking_overlay()

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

    @staticmethod
    def _format_file_size(size_in_bytes: int) -> str:
        """
        Converts a file size in bytes to a human-readable format (Bytes, KB, MB, GB, etc.).

        Args:
            size_in_bytes (int): The file size in bytes.

        Returns:
            str: Human-readable file size.
        """
        units = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']  # Add more if needed
        size = float(size_in_bytes)
        for unit in units:
            if size < 1024:
                return f"{size:.2f} {unit}"  # Format to 2 decimal places
            size /= 1024
        return f"{size:.2f} {units[-1]}"  # For extremely large sizes

    def _remove_selected_song(self, e: ft.ControlEvent):
        self.song_selector_info_column.controls[0] = self.song_selector

        # removes the selected song path from the saved paths
        self.selected_song_path = ""

        self.song_selector_info_column.update()

    async def _on_finish_sound_select(self, e: ft.FilePickerResultEvent):
        selected_files = e.files

        if not selected_files:
            return

        audio_file = selected_files[0]
        file_path: str = audio_file.path

        self.selected_song_path = file_path

        print(f"sent the slected path to {self.selected_song_path}")

        audio_file_details: ft.Container = ft.Container(
            padding=10,
            expand=True,
            content=ft.Row(
                expand=True,
                controls=[
                    ft.Container(
                        content=ft.Icon(ft.Icons.DELETE, color=ft.Colors.RED, size=25),
                        on_click=self._remove_selected_song
                    ),
                    ft.Text(f"{audio_file.name} | {self._format_file_size(audio_file.size)}", size=25),
                ]
            ),
            alignment=ft.Alignment(-1, 0)
        )

        self.song_selector_info_column.controls[0] = audio_file_details

        self.song_selector_info_column.update()

    # ---- image (sheet music) selection related stuff ----
    def _add_blocking_overlay(self):
        self.page.overlay.append(
            ft.Container(
                expand=True,
                bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
                content=ft.Text("Uploading", size=35, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                alignment=ft.Alignment(0, 0)
            )
        )

        self.page.update()

    def _remove_blocking_overlay(self):
        self.page.overlay.pop()

        self.page.update()

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

            image_remove_overlay: ft.Stack = ImageRemoveHover(
                image=image,
                image_name=image_name,
                width=image_container.width,
                height=image_container.height
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

        # scrolls to end (where the sheet_selector is)
        self.sheet_selector_row.scroll_to(offset=-1, duration=1000, curve=ft.AnimationCurve.EASE_IN_OUT)

    # -------------------------------------------------------

    def _initialize_file_selectors(self):
        self.song_selector = ft.Container(
            content=ft.Icon(ft.Icons.UPLOAD_ROUNDED, color=ft.Colors.GREY_800),
            on_click=self._select_sound_files,
            expand=True,
            expand_loose=True,
            height=150,
            border=ft.border.all(1, ft.Colors.GREY_800),
            border_radius=3,
            alignment=ft.Alignment(0, 0)
        )

        self.song_selector_info_column: ft.Column = ft.Column(
                    [
                        self.song_selector,
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Icon(ft.Icons.PLAY_ARROW_ROUNDED, ft.Colors.GREY_600, size=40),
                                    ft.Text(spans=[
                                        ft.TextSpan("0:00"), ft.TextSpan("/"), ft.TextSpan("0:00")
                                    ], weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600),
                                    ft.ProgressBar(
                                        value=0.01,
                                        height=5,
                                        expand_loose=True,
                                        expand=True,
                                        color=ft.Colors.GREY_600,
                                        bgcolor=ft.Colors.GREY_400,
                                        border_radius=10,
                                    ),
                                    ft.Icon(ft.Icons.VOLUME_UP_ROUNDED, ft.Colors.GREY_600, size=25),
                                ]
                            ),
                            border_radius=90,
                            padding=15,
                            height=75,
                            expand=True,
                            bgcolor=ft.Colors.with_opacity(0.7, ft.Colors.GREY_300),
                        ),
                    ],
                    height=150,
                    expand_loose=True,
                    expand=True,
                )

        self.song_selector_row: ft.Row = ft.Row(
            [
                ft.Container(
                    self.upload_cover_art_default_content,
                ),
                self.song_selector_info_column
            ],
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
            auto_scroll=False,
            scroll=ft.ScrollMode.ALWAYS,
            height=220,
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
                right=0, top=2, bottom=2, left=10
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
        song_info_parameters = ft.Container(
            padding=ft.Padding(
                right=25,
                left=25,
                top=5,
                bottom=5
            ),
            expand=8,
            content=ft.Container(
                padding=ft.Padding(
                    right=25,
                    left=25,
                    top=0,
                    bottom=0
                ),
                content=ft.Column(
                    [
                        ft.Container(
                            content=ft.Text("UPLOAD SONG",
                                            weight=ft.FontWeight.BOLD,
                                            color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE),
                                            size=35),
                            expand=True,
                            expand_loose=True,
                            alignment=ft.Alignment(0, 0),
                            padding=5,
                            height=65,
                            bgcolor=ft.Colors.BLUE_800,
                            border_radius=10
                        ),

                        ft.Column(
                            [
                                ft.Column(
                                    [
                                        ft.Text("Details", weight=ft.FontWeight.BOLD),

                                        self.song_selector_row,

                                        ft.Divider(),
                                    ]
                                ),
                                ft.Column(
                                    [
                                        self.song_info_row,
                                        # self.description_textbox,
                                        self.selected_genres_textbox,
                                    ]
                                ),
                            ],
                            spacing=20,
                        ),

                        ft.Divider(),

                        ft.Column(
                            [
                                ft.Text("Add Music Sheets", weight=ft.FontWeight.BOLD),
                                self.sheet_selector_row,
                            ]
                        ),

                        ft.Divider(),

                        # todo: clean up the code, and make it one button for an "everything upload"
                        # currently it is only for testing
                        ft.Row([
                            ft.Container(
                                height=55,
                                width=150,
                                border_radius=10,
                                content=ft.Text(
                                    "Clear information",
                                    weight=ft.FontWeight.W_500,
                                    color=ft.Colors.with_opacity(0.7, ft.Colors.RED_ACCENT_700),
                                    size=15,
                                ),
                                alignment=ft.Alignment(0, 0),
                                #bgcolor=ft.Colors.with_opacity(0.7, ft.Colors.RED_ACCENT_700)
                            ),
                            ft.Container(
                                height=55,
                                width=200,
                                bgcolor=ft.Colors.BLUE_800,
                                border_radius=10,
                                content=ft.Text(
                                    "Upload",
                                    weight=ft.FontWeight.W_500,
                                    color=ft.Colors.with_opacity(0.7, ft.Colors.WHITE),
                                    size=15,
                                ),
                                alignment=ft.Alignment(0, 0),
                                on_click=self._upload_all_files
                            ),
                        ],
                            alignment=ft.MainAxisAlignment.END
                        )
                    ],
                    tight=False,
                    spacing=20,
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    scroll=ft.ScrollMode.HIDDEN,
                ),
                expand=6,
                alignment=ft.Alignment(-1, -0.95)
            ),
            alignment=ft.Alignment(0, 0),
        )

        self.page_view = ft.Row(
            [
                self.sidebar,
                song_info_parameters,
            ],
            spacing=0,
            expand=True
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
    UploadPage(page=page).show()


if __name__ == "__main__":
    ft.app(main, assets_dir="Assets")
