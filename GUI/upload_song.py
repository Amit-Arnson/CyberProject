import flet as ft

from encryptions import EncryptedTransport
from pseudo_http_protocol import ClientMessage

from GUI.navigation_sidebar import NavigationSidebar


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

    def _select_files(self, e: ft.ControlEvent):
        self.file_picker.pick_files(
            allow_multiple=False
        )

    def _on_finish_select(self, e: ft.FilePickerUploadEvent):
        print(e)

    def _initialize_file_selector(self):
        self.file_picker_container = ft.Container(
            on_click=self._select_files,
            width=500,
            height=500,
            bgcolor=ft.Colors.RED
        )
    def _initialize_controls(self):
        self._initialize_sidebar_top()
        self._initialize_file_selector()

        # this is just a temporary container so that something takes that space up
        aa = ft.Container(
            expand=True,
            content=self.file_picker_container
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
