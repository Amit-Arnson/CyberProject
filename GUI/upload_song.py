import flet as ft

from encryptions import EncryptedTransport
from pseudo_http_protocol import ClientMessage

from GUI.navigation_sidebar import NavigationSidebar


class AutoFocusTextfield(ft.Stack):
    def __init__(self, width: int):
        super().__init__()
        self.values: list[str] = []

        self.text_padding = self.calculate_text_padding()

        self.value_container = ft.Container(
            height=50,
            width=width,
            expand=True,
            padding=10,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.START
            )
        )

        self.textfield = ft.TextField(
            multiline=False,
            content_padding=ft.Padding(left=self.text_padding, right=0, top=0, bottom=0),
            on_submit=self.on_finish
        )

        self.controls = [
            self.value_container,
            self.textfield
        ]

    def calculate_text_padding(self):
        return sum([len(value) for value in self.values]) * 11.5 + 10

    def update_text_padding(self):
        self.text_padding = self.calculate_text_padding()

    def on_finish(self, e):
        value = self.textfield.value
        self.values.append(value)

        tag_text_container = ft.Container(
            height=30,
            width=len(value) * 10,
            bgcolor=ft.Colors.RED,
            border_radius=5,
            content=ft.Text(value),
            alignment=ft.Alignment(0, 0)
        )

        self.value_container.content.controls.append(
            tag_text_container
        )

        self.update_text_padding()
        self.textfield.value = None
        self.textfield.autofocus = True
        self.textfield.content_padding = ft.Padding(left=self.text_padding, right=0, top=0, bottom=0)

        self.update()




class UploadPage:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.LIGHT

        self.page_width = 1200
        self.page_height = 700

        self.transport: EncryptedTransport | None = None
        if hasattr(page, "transport"):
            self.transport: EncryptedTransport = page.transport

        self.sidebar = NavigationSidebar()

        self.file_picker = ft.FilePicker()
        self.file_picker.on_result = self._on_finish_select

        # add the file picker control to the page
        self.page.overlay.append(self.file_picker)

        self._initialize_controls()

    def _initialize_sidebar_top(self):
        self.sidebar.top_part.margin = ft.Margin(top=10, bottom=0, right=0, left=0)

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
        self.file_picker.pick_files(
            allow_multiple=False,
            file_type=ft.FilePickerFileType.AUDIO
        )

    def _select_image_files(self, e: ft.ControlEvent):
        self.file_picker.pick_files(
            allow_multiple=True,
            file_type=ft.FilePickerFileType.IMAGE
        )

    def _on_finish_select(self, e: ft.FilePickerUploadEvent):
        print(e)

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

        # self.song_band_textbox = ft.TextField(
        #     label="song band",
        # )

        self.song_band_textbox = AutoFocusTextfield(
            width=500,
        )

    def _initialize_genre_tag_textbox(self):
        self.selected_genres_textbox = ft.TextField(
            label="genres",
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
