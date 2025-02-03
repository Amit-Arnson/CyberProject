import flet as ft

from encryptions import EncryptedTransport
from Caches.user_cache import ClientSideUserCache

from pseudo_http_protocol import ClientMessage


# todo: add the logo somewhere? idk
class SignupPage:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.LIGHT

        self.transport: EncryptedTransport | None = None
        if hasattr(page, "transport"):
            self.transport: EncryptedTransport = page.transport

        # the user cache is not needed in login (since we don't have a session token assigned yet)
        # self.user_cache: ClientSideUserCache | None = None
        # if hasattr(page, "user_cache"):
        #     self.user_cache: ClientSideUserCache = page.user_cache

        self._initialize_controls()

    @staticmethod
    def _full_border(border_color: ft.Colors):
        border = ft.Border(
            top=ft.BorderSide(width=1, color=border_color),
            bottom=ft.BorderSide(width=1, color=border_color),
            right=ft.BorderSide(width=1, color=border_color),
            left=ft.BorderSide(width=1, color=border_color)
        )

        return border

    def _initialize_username(self, border_color: ft.Colors = ft.Colors.GREY):
        self.username_textbox = ft.TextField(
            max_length=20,
            expand=True,
            height=50,
            label="username",
            border=ft.InputBorder.NONE,
            content_padding=10,
            error_style=ft.TextStyle(-10)
        )

        self.username_decoration = ft.Container(
            content=ft.Icon(ft.Icons.PERSON),
            height=50,
            width=50,
            border=ft.Border(
                right=ft.BorderSide(width=1, color=border_color),
            ),
        )

        self.username_decoration_row = ft.Row(
            [
                self.username_decoration,
                self.username_textbox
            ],
            spacing=0,
            expand=True
        )

        self.username_container = ft.Container(
            content=self.username_decoration_row,
            border=self._full_border(border_color),
        )

    def _initialize_display_name(self, border_color: ft.Colors = ft.Colors.GREY):
        self.display_name_textbox = ft.TextField(
            max_length=20,
            expand=True,
            height=50,
            label="display name",
            border=ft.InputBorder.NONE,
            content_padding=10,
            error_style=ft.TextStyle(-10)
        )

        self.display_name_decoration = ft.Container(
            content=ft.Icon(ft.Icons.PERSON),
            height=50,
            width=50,
            border=ft.Border(
                right=ft.BorderSide(width=1, color=border_color),
            ),
        )

        self.display_name_decoration_row = ft.Row(
            [
                self.display_name_decoration,
                self.display_name_textbox
            ],
            spacing=0,
            expand=True
        )

        self.display_name_container = ft.Container(
            content=self.display_name_decoration_row,
            border=self._full_border(border_color),
        )

    def _initialize_password(self, border_color: ft.Colors = ft.Colors.GREY):
        self.password_textbot = ft.TextField(
            password=True,
            can_reveal_password=True,
            max_length=20,
            height=50,
            expand=True,
            label="password",
            border=ft.InputBorder.NONE,
            content_padding=10,
            error_style=ft.TextStyle(-10)
        )

        self.password_decoration = ft.Container(
            content=ft.Icon(ft.Icons.LOCK),
            height=50,
            width=50,
            border=ft.Border(
                right=ft.BorderSide(width=1, color=border_color),
            ),
        )

        self.password_decoration_row = ft.Row(
            [
                self.password_decoration,
                self.password_textbot
            ],
            spacing=0,
            expand=True
        )

        self.password_container = ft.Container(
            content=self.password_decoration_row,
            border=self._full_border(border_color),
        )

    def _initialize_confirm_password(self, border_color: ft.Colors = ft.Colors.GREY):
        self.confirm_password_textbox = ft.TextField(
            password=True,
            can_reveal_password=True,
            max_length=20,
            height=50,
            expand=True,
            label="confirm password",
            border=ft.InputBorder.NONE,
            content_padding=10,
            error_style=ft.TextStyle(-10)
        )

        self.confirm_password_decoration = ft.Container(
            content=ft.Icon(ft.Icons.PERSON),
            height=50,
            width=50,
            border=ft.Border(
                right=ft.BorderSide(width=1, color=border_color),
            ),
        )

        self.confirm_password_decoration_row = ft.Row(
            [
                self.confirm_password_decoration,
                self.confirm_password_textbox
            ],
            spacing=0,
            expand=True
        )

        self.confirm_password_container = ft.Container(
            content=self.confirm_password_decoration_row,
            border=self._full_border(border_color),
        )

    def _initialize_buttons(self):
        self.login_button = ft.Button(
            bgcolor=ft.Colors.BLUE,
            content=ft.Text("LOGIN", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            width=self.page.width,
            height=self.page.height / 12,
            on_click=self._switch_to_login
        )

        self.signup_button = ft.Button(
            bgcolor=ft.Colors.WHITE,
            content=ft.Text("SIGNUP", weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
            width=self.page.width,
            height=self.page.height / 12,
            style=ft.ButtonStyle(
                side={ft.ControlState.DEFAULT: ft.BorderSide(1, ft.Colors.BLACK)}
            ),
            on_click=self._send_signup
        )

    def _initialize_divider(self):
        # the use of a stack here is to lay the Container that has the "or" text on TOP of the divider.
        self.horizontal_button_divider = ft.Stack(
            controls=[
                ft.Divider(
                    thickness=1,
                    color=ft.Colors.GREY,
                ),
                ft.Container(
                    content=ft.Text(
                        "already have an account?",
                        color=ft.Colors.GREY,
                        weight=ft.FontWeight.BOLD,
                        size=self.page.height / 46
                    ),
                    bgcolor=self.page.bgcolor if self.page.bgcolor else ft.Colors.WHITE,
                    height=self.page.height / 30,
                    width=self.page.width / 6,
                    alignment=ft.Alignment(0, 0),
                )
            ],
            height=self.page.height / 25,
            alignment=ft.Alignment(0, 0)
        )

    def _initialize_text(self):
        self.login_text = ft.Text("Login", size=50)
        self.login_sub_text = ft.Text("Log in to your jambox account!", size=20, color=ft.Colors.GREY_600)
        self.login_text_container = ft.Container(
            ft.Column(
                [
                    self.login_text,
                    self.login_sub_text
                ],
            )
        )

    def _initialize_controls(self):
        self._initialize_username()
        self._initialize_display_name()
        self._initialize_password()
        self._initialize_confirm_password()

        self._initialize_buttons()
        self._initialize_divider()

        self._initialize_text()

        self.login_content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Column(
                        [
                            ft.Column([
                                self.login_text_container,

                                self.username_container,
                                self.display_name_container,
                                self.password_container,
                                self.confirm_password_container,
                            ]),

                            ft.Column(
                                [
                                    self.signup_button,
                                    self.horizontal_button_divider,
                                    self.login_button,
                                ],
                                spacing=13
                            )
                        ],
                        spacing=25,
                    ),
                ],
                spacing=12,
                expand=True
            ),
            width=self.page.width / 3,
            padding=10,
            alignment=ft.Alignment(0, 0)
        )

        self.spaced_content = ft.Column(
            [
                # the empty containers are there for the spacing of the items, so that the login content will be
                # in the middle of the right side.
                ft.Container(height=80, width=self.page.width/3),
                self.login_content,
                ft.Container(height=180, width=self.page.width/3, expand=True, )
            ],
            alignment=ft.MainAxisAlignment.START,
        )

        self.right_side = ft.Container(
            content=self.spaced_content,
            expand=False,
            bgcolor=ft.Colors.WHITE,
            padding=0,
        )

        self.left_side = ft.Container(
            expand=True,
            bgcolor=ft.Colors.BLUE_900,
            padding=0,
        )

        self.page_view = ft.Row(
            controls=[
                self.right_side,
                self.left_side
            ],
            expand=True,
            spacing=0,
        )

    # todo: fix the issue where it ruins the page view when it opens the banner
    def _raise_error_banner(self, error: ft.Control):
        """
            accepts the control which will be displayed to the user.
            this means you can style texts to contain clickable "links"
        """

        def close_banner(e):
            self.page.close(banner)

        action_button_style = ft.ButtonStyle(color=ft.Colors.BLUE)
        banner = ft.Banner(
            bgcolor=ft.Colors.AMBER_100,
            leading=ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.AMBER, size=40),
            content=error,
            actions=[
                ft.TextButton(text="OK", style=action_button_style, on_click=close_banner),
            ],
            open=True
        )

        self.page.add(banner)

    def _switch_to_login(self, e):
        # importing LoginPage inside the function so that circular import error doesn't happen.
        # this is because the import only happens when the button is clicked, and not loaded when the page loads initially.
        from GUI.login import LoginPage

        LoginPage(self.page).show()

    def _send_signup(self, e):
        """
        send the login request to the server with the input values from the user.

        endpoint: user/login (POST)

        expected payload (to server):
        {
            "username": str,
            "display_name": str,
            "password": str
        }

        expected output (from server):
        {
            "user_id": str,
        }

        this function will then automatically log the user in.
        the signup endpoint in the server does not log in automatically, and thus it must be done as different action.

        expected payload (to server):
        {
            "username": str,
            "password": str
        }

        expected output (from server):
        {
            "session_token": str,
            "user_id": str,
        }
        """

        print("here")

        # todo: implement a minimum length check (server-side and client side)
        username = self.username_textbox.value
        display_name = self.display_name_textbox.value

        # passwords are stripped of whitespaces
        password = self.password_textbot.value.strip()
        confirm_password = self.confirm_password_textbox.value.strip()

        # reset any currently showing error
        self.confirm_password_textbox.error_text = None
        self.username_textbox.error_text = None
        self.password_textbot.error_text = None
        self.display_name_textbox.error_text = None

        self.page.update()

        if password != confirm_password:
            self.confirm_password_textbox.error_text = "password does not match up!"

            # despite us updating the
            self.confirm_password_textbox.update()
            return

        if self.transport:
            # create the account by signing the user in.
            self.transport.write(
                ClientMessage(
                    authentication=None,
                    endpoint="user/signup/login",
                    method="post",
                    payload={
                        "username": username,
                        "display_name": display_name,
                        "password": password
                    }
                ).encode()
            )
        else:
            error_text = ft.Text(
                value="There seems to have been an error when trying to submit login information (code 1001)",
                color=ft.Colors.BLACK,
            )
            self._raise_error_banner(error_text)

    def show(self, clear: bool = True):
        """:param clear: whether to clear the page before trying to add the page's content or not."""

        if clear:
            self.page.clean()

        self.page.view = self
        self.page.add(self.page_view)

        self.page.update()

def main(page: ft.Page):
    SignupPage(page=page).show()


if __name__ == "__main__":
    ft.app(main, assets_dir="Assets")
