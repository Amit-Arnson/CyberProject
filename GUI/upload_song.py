import flet as ft

from encryptions import EncryptedTransport

from GUI.Controls.navigation_sidebar import NavigationSidebar
from GUI.Controls.tag_input import TagInput


class UploadPage:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.LIGHT

        # these are the max available size of the screen
        self.page_width = page.window.width
        self.page_height = page.window.height

        self.selected_song_path: str = ""
        self.selected_sheet_paths: list[str] = []

        self.transport: EncryptedTransport | None = None
        if hasattr(page, "transport"):
            self.transport: EncryptedTransport = page.transport

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
            ft.Stack(
                [
                    ft.Container(
                        width=90,
                        height=75,
                        bgcolor=ft.Colors.BLUE_900,
                        shape=ft.BoxShape.CIRCLE,
                        right=-1,
                    ),
                    ft.Container(
                        width=320,
                        # this is the closest ive managed to make it look like 1 piece
                        height=75.19,
                        bgcolor=ft.Colors.BLUE_900,
                        left=0,
                        content=ft.Text(
                            "Upload Song", size=25, color=ft.Colors.BLUE_700,
                            weight=ft.FontWeight.BOLD
                        ),
                        alignment=ft.Alignment(0, 0)
                    ),
                ]
            ),
            width=500,
            height=100,
        )

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

    def _on_finish_sound_select(self, e: ft.FilePickerResultEvent):
        selected_files = e.files
        print(e.files)
        print("selected audio")

    def _on_finish_image_select(self, e: ft.FilePickerResultEvent):
        print(e.files)
        print("selected image")

    def _initialize_file_selectors(self):
        self.song_selector = ft.Container(
            on_click=self._select_sound_files,
            width=100,
            height=50,
            bgcolor=ft.Colors.RED
        )

        self.sheet_selector = ft.Container(
            on_click=self._select_image_files,
            width=100,
            height=50,
            bgcolor=ft.Colors.GREY
        )

    def _initialize_song_info_textbox(self):
        self.song_name_textbox = ft.TextField(
            label="song name",
        )

        self.song_album_textbox = ft.TextField(
            label="song album",
        )

        self.song_band_textbox = ft.TextField(
            label="song band",
        )

    def _initialize_genre_tag_textbox(self):
        self.selected_genres_textbox = TagInput(
            border_radius=5,
            border=ft.border.all(color=ft.Colors.BLACK),
            padding=ft.Padding(
                right=0, top=2, bottom=2, left=2
            ),
            tag_spacing=5,
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
            expand=True,
            content=ft.Column(
                [
                    self.song_selector,
                    self.sheet_selector,
                    self.song_name_textbox,
                    self.song_album_textbox,
                    self.song_band_textbox,
                    self.description_textbox,
                    self.selected_genres_textbox
                ]
            )
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
