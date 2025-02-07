import flet as ft


class NavigationSidebar(ft.Container):
    def __init__(self):
        super().__init__()
        self.page_width = 1200
        self.page_height = 700

        self.sidebar_width = self.page_width / 3.3

        self._initialize_sidebar()

        self.content = ft.Column(
            [
                self.top_part,
                self.middle_part,
                self.bottom_part
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        self.bgcolor = ft.Colors.BLUE

    @staticmethod
    def _sidebar_item_hover(e: ft.ControlEvent):
        item: ft.Container = e.control

        # the e.data is a string of "true" or "false"
        is_currently_hovering = e.data

        if is_currently_hovering == "true":
            item.bgcolor = ft.Colors.with_opacity(0.5, ft.Colors.WHITE)
            item.border = ft.Border(
                left=ft.BorderSide(width=5, color=ft.Colors.WHITE)
            )
        else:
            item.bgcolor = None
            item.border = None

        item.update()

    def _initialize_sidebar_items(self):
        item_height = self.page_height / 10

        self.goto_tempo_finder = ft.Container(
            on_click=lambda _: print("went to tempo finder"),
            on_hover=self._sidebar_item_hover,
            height=item_height,
            width=self.sidebar_width,
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.MENU),
                    ft.Text("TEMPO FINDER")
                ],
            ),
            padding=10,
        )

        self.goto_ai_chat = ft.Container(
            on_click=lambda _: print("went to ai chat"),
            on_hover=self._sidebar_item_hover,
            height=item_height,
            width=self.sidebar_width,
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.MENU),
                    ft.Text("AI CHAT")
                ]
            ),
            padding=10,
        )

        self.goto_upload_song = ft.Container(
            on_click=lambda _: print("went to upload song"),
            on_hover=self._sidebar_item_hover,
            height=item_height,
            width=self.sidebar_width,
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.MENU),
                    ft.Text("UPLOAD SONG")
                ]
            ),
            padding=10,
        )

    def _initialize_sidebar_bottom_item(self):
        item_height = self.page_height / 10

        self.settings = ft.Container(
            on_click=lambda _: print("went to settings"),
            on_hover=self._sidebar_item_hover,
            height=item_height,
            width=self.sidebar_width,
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.MENU),
                    ft.Text("SETTINGS")
                ]
            ),
            padding=10,
        )

        self.logout = ft.Container(
            on_click=lambda _: print("went to logout"),
            on_hover=self._sidebar_item_hover,
            height=item_height,
            width=self.sidebar_width,
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.MENU),
                    ft.Text("LOGOUT")
                ]
            ),
            padding=10,
        )

    def _initialize_sidebar(self):
        self._initialize_sidebar_items()
        self._initialize_sidebar_bottom_item()

        self.top_part = ft.Container(
            height=80,
            width=self.sidebar_width,
            content=ft.Text("Upload Song"),
            alignment=ft.Alignment(0, 0)
        )

        self.middle_part = ft.Container(
            content=ft.Column(
                [
                    self.goto_upload_song,
                    self.goto_ai_chat,
                    self.goto_tempo_finder
                ]
            ),
            expand=True,
            alignment=ft.Alignment(0, 0)
        )

        self.bottom_part = ft.Container(
            content=ft.Column(
                [
                    self.settings,
                    self.logout
                ]
            ),
            width=self.sidebar_width,
        )