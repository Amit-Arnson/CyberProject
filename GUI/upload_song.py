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

    def _initialize_sidebar_top(self):
        self.sidebar.top_part.margin = ft.Margin(top=10, bottom=0, right=0, left=0)
        # self.sidebar.top_part.content = ft.Stack(
        #     [
        #         ft.Container(
        #             content=ft.Text("Upload Song", size=25, color=ft.Colors.BLUE_600),
        #             bgcolor=ft.Colors.BLUE_900,
        #             height=100,
        #             width=280,
        #             alignment=ft.Alignment(0, 0)
        #         ),
        #         ft.Container(
        #             ft.Container(
        #                 expand=True,
        #                 bgcolor=ft.Colors.BLUE_100,
        #                 shape=ft.BoxShape.CIRCLE,
        #             ),
        #             right=0,
        #         )
        #     ],
        # )

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
                        height=75.5,
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
            padding=ft.Padding(right=0, bottom=0, left=0, top=5),
            width=500,
            height=100,
        )

    def _initialize_controls(self):
        self._initialize_sidebar_top()

        aa = ft.Container(
            expand=True,
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
