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

        self._initialize_controls()


    def _initialize_controls(self):
        aa = ft.Container(
            expand=True,
            bgcolor=ft.Colors.GREY,
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
