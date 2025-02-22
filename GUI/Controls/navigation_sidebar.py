import flet as ft


class NavigationSidebar(ft.Container):
    def __init__(self):
        super().__init__()

        # these are the max available size of the screen
        self.page_width = self.page.window.width
        self.page_height = self.page.window.height

        self.sidebar_width = self.page_width / 3.3

        self.item_text_values = {
            "color": ft.Colors.WHITE70,
            "weight": ft.FontWeight.BOLD
        }

        self.item_icon_values = {
            "color": ft.Colors.WHITE70
        }

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

    def _switch_to_upload_song(self, e: ft.ControlEvent):
        """switches the page to the "upload song" page"""
        from GUI.upload_song import UploadPage

        UploadPage(self.page).show()

    def _switch_to_tempo_finder(self, e: ft.ControlEvent):
        """switches the page to the "tempo finder" page"""

        # todo: implement tempo finder
        print("went to tempo finder")

    def _switch_to_ai_chat(self, e: ft.ControlEvent):
        """switches the page to the "AI chat" page"""

        # todo: implement AI chat
        print("went to Ai chat")

    def _initialize_sidebar_items(self):
        item_height = self.page_height / 10

        self.goto_tempo_finder = ft.Container(
            on_click=self._switch_to_tempo_finder,
            on_hover=self._sidebar_item_hover,
            height=item_height,
            width=self.sidebar_width,
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.MUSIC_NOTE, **self.item_icon_values),
                    ft.Text("TEMPO FINDER", **self.item_text_values)
                ],
            ),
            padding=10,
        )

        self.goto_ai_chat = ft.Container(
            on_click=self._switch_to_ai_chat,
            on_hover=self._sidebar_item_hover,
            height=item_height,
            width=self.sidebar_width,
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.CHAT, **self.item_icon_values),
                    ft.Text("AI CHAT", **self.item_text_values)
                ]
            ),
            padding=10,
        )

        self.goto_upload_song = ft.Container(
            on_click=self._switch_to_upload_song,
            on_hover=self._sidebar_item_hover,
            height=item_height,
            width=self.sidebar_width,
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.UPLOAD_FILE, **self.item_icon_values),
                    ft.Text("UPLOAD SONG", **self.item_text_values)
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
                    ft.Icon(ft.Icons.SETTINGS, **self.item_icon_values),
                    ft.Text("SETTINGS", **self.item_text_values)
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
                    ft.Icon(ft.Icons.LOGOUT, **self.item_icon_values),
                    ft.Text("LOGOUT", **self.item_text_values)
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
