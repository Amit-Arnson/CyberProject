import flet as ft

from encryptions import EncryptedTransport
from Caches.user_cache import ClientSideUserCache

from GUI.Controls.navigation_sidebar import NavigationSidebar

from pseudo_http_protocol import ClientMessage

import hashlib


class Settings:
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

        self.user_cache: ClientSideUserCache | None = None
        if hasattr(page, "user_cache"):
            self.user_cache: ClientSideUserCache = page.user_cache

        self.sidebar = NavigationSidebar(self.page)

        self.sidebar.settings.on_click = None

        # the sidebar is set to 2 and the right side of the page is set to 10. this means the sidebar takes 20% of the
        # available screen
        self.sidebar.expand = 2

        self._initialize_controls()

    def upload_statistics(self, total_song_uploads: int, total_comments: int):
        self.song_uploads.value = f"{total_song_uploads}"
        self.comment_uploads.value = f"{total_comments}"

        self.page.update()

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

    def _initialize_username(self):
        username = self.user_cache.username

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

        self.username_row = ft.Row(
            [
                user_avatar,
                ft.Text(username, size=35)
            ]
        )

    def _initialize_upload_amounts(self):
        self.song_uploads = ft.Text("0", weight=ft.FontWeight.W_500, size=20)
        self.comment_uploads = ft.Text("0", weight=ft.FontWeight.W_500, size=20)

        self.song_uploads_label = ft.Container(
            content=ft.Row(
                [
                    ft.Text("Total Uploaded Songs:", weight=ft.FontWeight.W_500, size=25),
                    self.song_uploads
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            )
        )

        self.comment_uploads_label = ft.Container(
            content=ft.Row(
                [
                    ft.Text("Total Written Comments:", weight=ft.FontWeight.W_500, size=25),
                    self.comment_uploads
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            )
        )

    def _open_display_edit(self, *args):
        self.edit_display_name_field.read_only = False
        self.edit_display_name_field.mouse_cursor = ft.MouseCursor.BASIC
        self.edit_display_name_field.update()

        self.edit_display_name_field.focus()

    def _reset_display_edit(self, *args):
        self.edit_display_name_field.read_only = True
        self.edit_display_name_field.mouse_cursor = ft.MouseCursor.FORBIDDEN
        self.edit_display_name_field.value = self.user_cache.display_name

        self.edit_display_name_field.update()

    def _submit_display_edit(self, *args):
        self.edit_display_name_field.read_only = True
        self.edit_display_name_field.mouse_cursor = ft.MouseCursor.FORBIDDEN
        self._reqeust_edit_display_name()

        self.edit_display_name_field.update()

    def _initialize_edit_display_name(self):
        display_name = self.user_cache.display_name

        self.edit_display_name_field = ft.TextField(
            value=display_name,
            read_only=True,
            mouse_cursor=ft.MouseCursor.FORBIDDEN,
            on_blur=self._reset_display_edit,
            on_submit=self._submit_display_edit,
            border=ft.InputBorder.NONE,
        )

        self.edit_display_name_button = ft.Container(
            content=ft.Text("Edit"),
            bgcolor=ft.Colors.BLUE_300,
            border_radius=10,
            width=100,
            height=50,
            alignment=ft.Alignment(0, 0),
            on_click=self._open_display_edit
        )

        self.edit_display_name = ft.Container(
            ft.Row(
                [
                    self.edit_display_name_field,
                    self.edit_display_name_button
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            border=ft.border.all(1, ft.Colors.BLACK),
            border_radius=10,
            padding=10,
            width=450,
            height=75
        )

    def _initialize_delete_account(self):
        self.confirm_delete_account = ft.AlertDialog(
            content=ft.Container(
                width=200,
                height=150,
                bgcolor=ft.Colors.WHITE,
                border_radius=10,
                padding=10,
                content=ft.Column(
                    [
                        ft.Text("Are you sure you want to delete your account? this action is not reversible"),
                        ft.Row(
                            [
                                ft.Container(
                                    ft.Text("Delete"),
                                    border_radius=10,
                                    width=100,
                                    height=50,
                                    alignment=ft.Alignment(0, 0),
                                    bgcolor=ft.Colors.RED,
                                    on_click=self._request_delete_account
                                ),
                                ft.Container(
                                    ft.Text("Cancel"),
                                    border_radius=10,
                                    width=100,
                                    height=50,
                                    alignment=ft.Alignment(0, 0),
                                    bgcolor=ft.Colors.GREY,
                                    on_click=lambda _: self.page.close(self.confirm_delete_account)
                                )
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        )
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                )
            ),
            bgcolor=ft.Colors.with_opacity(0, ft.Colors.WHITE)
        )

        self.delete_account_button = ft.Container(
            content=ft.Text("Delete Account"),
            border_radius=10,
            width=150,
            height=50,
            alignment=ft.Alignment(0, 0),
            bgcolor=ft.Colors.RED,
            on_click=lambda _: self.page.open(self.confirm_delete_account)
        )

    def _request_upload_information(self):
        self.transport.write(
            ClientMessage(
                authentication=self.user_cache.session_token,
                method="get",
                endpoint="user/statistics",
                payload={"empty": True}
            ).encode()
        )

    def _request_delete_account(self, *args):
        self.transport.write(
            ClientMessage(
                authentication=self.user_cache.session_token,
                method="delete",
                endpoint="user/delete",
                payload={"empty": True}
            ).encode()
        )

    def _reqeust_edit_display_name(self):
        self.transport.write(
            ClientMessage(
                authentication=self.user_cache.session_token,
                method="post",
                endpoint="user/edit/display",
                payload={"display_name": self.edit_display_name_field.value}
            ).encode()
        )

    def _initialize_controls(self):
        self._initialize_username()
        self._initialize_upload_amounts()
        self._initialize_edit_display_name()
        self._initialize_delete_account()

        self._request_upload_information()

        self.page_view = ft.Row(
            controls=[
                self.sidebar,
                ft.Container(
                    ft.Column(
                        [
                            self.username_row,

                            ft.Container(
                                bgcolor=ft.Colors.GREY_400,
                                width=300,
                                height=1,
                            ),

                            ft.Text(
                                "Statistics",
                                color=ft.Colors.GREY,
                                size=25,
                                weight=ft.FontWeight.W_300
                            ),

                            ft.Column(
                                [
                                    self.song_uploads_label,
                                    self.comment_uploads_label,
                                ],
                                spacing=10,
                            ),

                            ft.Divider(),

                            ft.Container(
                                ft.Text(
                                    "Edit",
                                    color=ft.Colors.GREY,
                                    size=25,
                                    weight=ft.FontWeight.W_300
                                ),
                                padding=ft.Padding(
                                    top=0,
                                    right=0,
                                    left=0,
                                    bottom=5,
                                ),
                            ),

                            self.edit_display_name,

                            ft.Container(
                                bgcolor=ft.Colors.GREY_400,
                                width=150,
                                height=1,
                            ),

                            self.delete_account_button
                        ]
                    ),
                    expand=8,
                    padding=10
                )
            ],
            expand=True,
            spacing=0,
        )

    def append_error(self, error_control: ft.Control):
        current_last_control_data = self.page_view.controls[-1].data

        if isinstance(current_last_control_data, dict)\
                and isinstance(error_control.data, dict)\
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
    Settings(page=page).show()


if __name__ == "__main__":
    ft.app(main, assets_dir="Assets")
