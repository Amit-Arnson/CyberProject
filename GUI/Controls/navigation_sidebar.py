import hashlib

import flet as ft


class NavigationSidebar(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page = page

        # these sizes are the optimal ratio for the average PC screen
        self.page_width = 1280
        self.page_height = 720

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
    def _string_to_hex_color(string: str) -> str:

        hash_bytes = hashlib.sha256(string.encode()).digest()
        r, g, b = hash_bytes[0], hash_bytes[1], hash_bytes[2]

        # force the color to be on the lighter side by blending toward white (255)
        # we need to do this because making a system that switches the profile image letter's color from white to black
        # is much harder than just ensuring that the background color is light.
        def lighten(value, min_brightness=180):
            return int(value * 0.5 + 255 * 0.5) if value < min_brightness else value

        r, g, b = lighten(r), lighten(g), lighten(b)
        color = f'#{r:02x}{g:02x}{b:02x}'

        return color

    def _create_avatar(self):
        username = "username"
        if hasattr(self.page, "user_cache"):
            username = self.page.user_cache.username

        user_avatar = ft.Container(
            ft.Container(
                content=ft.Text(username[0], size=25),
                bgcolor=self._string_to_hex_color(username),
                alignment=ft.Alignment(0, 0),
                border_radius=360,
                width=60,
                height=60,
                border=ft.border.all(width=1, color=ft.Colors.GREY_700),
            ),
            alignment=ft.Alignment(0, 0)
        )

        user_name = ft.Container(
            ft.Text(username, size=20, weight=ft.FontWeight.W_500),
            alignment=ft.Alignment(0, 0)
        )

        return ft.Container(
            ft.Column(
                [
                    user_avatar,
                    user_name
                ],
                spacing=0,
            ),
            padding=5,
        )

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

    def _switch_to_home_page(self, e: ft.ControlEvent):
        from GUI.home_page import HomePage

        HomePage(self.page).show()

    def _switch_to_tempo_finder(self, e: ft.ControlEvent):
        from GUI.tempo_finder import AudioInformation

        AudioInformation(self.page).show()

    def _switch_to_settings(self, e: ft.ControlEvent):
        from GUI.settings import Settings

        Settings(self.page).show()

    def _logout(self, e: ft.ControlEvent):
        from client_actions import user_logout

        user_logout(self.page)

    def _initialize_sidebar_items(self):
        item_height = self.page_height / 10

        self.goto_tempo_finder = ft.Container(
            on_click=self._switch_to_tempo_finder,
            on_hover=self._sidebar_item_hover,
            height=item_height,
            expand=True,
            expand_loose=True,
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.MUSIC_NOTE, **self.item_icon_values),
                    ft.Text("TEMPO FINDER", **self.item_text_values)
                ],
            ),
            padding=10,
        )

        self.goto_upload_song = ft.Container(
            on_click=self._switch_to_upload_song,
            on_hover=self._sidebar_item_hover,
            height=item_height,
            expand=True,
            expand_loose=True,
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.UPLOAD_FILE, **self.item_icon_values),
                    ft.Text("UPLOAD SONG", **self.item_text_values)
                ]
            ),
            padding=10,
        )

        self.goto_home_page = ft.Container(
            on_click=self._switch_to_home_page,
            on_hover=self._sidebar_item_hover,
            height=item_height,
            expand=True,
            expand_loose=True,
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.HOME_ROUNDED, **self.item_icon_values),
                    ft.Text("HOME", **self.item_text_values)
                ]
            ),
            padding=10,
        )

    def _initialize_sidebar_bottom_item(self):
        item_height = self.page_height / 10

        self.settings = ft.Container(
            on_click=self._switch_to_settings,
            on_hover=self._sidebar_item_hover,
            height=item_height,
            expand=True,
            expand_loose=True,
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.SETTINGS, **self.item_icon_values),
                    ft.Text("SETTINGS", **self.item_text_values)
                ]
            ),
            padding=10,
        )

        self.logout = ft.Container(
            on_click=self._logout,
            on_hover=self._sidebar_item_hover,
            height=item_height,
            expand=True,
            expand_loose=True,
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
            self._create_avatar(),
            expand=2,
            alignment=ft.Alignment(0, 0)
        )

        self.middle_part = ft.Container(
            content=ft.Column(
                [
                    self.goto_home_page,
                    self.goto_upload_song,
                    self.goto_tempo_finder
                ]
            ),
            expand=10,
        )

        self.bottom_part = ft.Container(
            content=ft.Column(
                [
                    self.settings,
                    self.logout
                ]
            ),
        )
