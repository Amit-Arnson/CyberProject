import flet as ft

from encryptions import EncryptedTransport
from Caches.user_cache import ClientSideUserCache

from pseudo_http_protocol import ClientMessage


class LoginPage:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.LIGHT

        # these sizes are the optimal ratio for the average PC screen
        self.page_width = 1280
        self.page_height = 720

        self.textbox_size = 55

        # since the "password" type text fields have an eye icon to be able to turn off visible/invisible password,
        # the text field itself needs to be set down a little lower (so that the eye is centered)
        self.password_offset = 5

        self.transport: EncryptedTransport | None = None
        if hasattr(page, "transport"):
            self.transport: EncryptedTransport = page.transport

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

    @staticmethod
    def _clear_textfield_error(e: ft.ControlEvent):
        text_field: ft.TextField = e.control

        if not text_field.error_text:
            return

        text_field.error_text = None

        text_field.update()

    def _initialize_username(self, border_color: ft.Colors = ft.Colors.GREY):
        self.username_textbox = ft.TextField(
            max_length=20,
            expand=True,
            height=self.textbox_size,
            label="username",
            border=ft.InputBorder.NONE,
            content_padding=10,
            on_focus=self._clear_textfield_error,
            error_style=ft.TextStyle(height=-1)
        )

        self.username_decoration = ft.Container(
            content=ft.Icon(ft.Icons.PERSON),
            height=self.textbox_size,
            width=self.textbox_size,
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

    def _initialize_password(self, border_color: ft.Colors = ft.Colors.GREY):
        self.password_textbox = ft.TextField(
            password=True,
            can_reveal_password=True,
            max_length=20,
            height=self.textbox_size - self.password_offset,
            expand=True,
            label="password",
            border=ft.InputBorder.NONE,
            content_padding=10,
            on_focus=self._clear_textfield_error,
            error_style=ft.TextStyle(height=-1),
        )

        self.password_decoration = ft.Container(
            content=ft.Icon(ft.Icons.LOCK),
            height=self.textbox_size,
            width=self.textbox_size,
            border=ft.Border(
                right=ft.BorderSide(width=1, color=border_color),
            ),
        )

        self.password_decoration_row = ft.Row(
            [
                self.password_decoration,
                self.password_textbox
            ],
            spacing=0,
            expand=True
        )

        self.password_container = ft.Container(
            content=self.password_decoration_row,
            border=self._full_border(border_color),
        )

    def _initialize_buttons(self):
        self.login_button = ft.Button(
            bgcolor=ft.Colors.BLUE,
            content=ft.Text("LOGIN", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            width=self.page_width,
            height=self.page_height / 12,
            on_click=self._send_login
        )

        self.signup_button = ft.Button(
            bgcolor=ft.Colors.WHITE,
            content=ft.Text("SIGNUP", weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
            width=self.page_width,
            height=self.page_height / 12,
            style=ft.ButtonStyle(
                side={ft.ControlState.DEFAULT: ft.BorderSide(1, ft.Colors.BLACK)}
            ),
            on_click=self._switch_to_signup
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
                        "don't have an account?",
                        color=ft.Colors.GREY,
                        weight=ft.FontWeight.BOLD,
                        size=self.page_height / 46
                    ),
                    bgcolor=self.page.bgcolor if self.page.bgcolor else ft.Colors.WHITE,
                    height=self.page_height / 30,
                    width=self.page_width / 6,
                    alignment=ft.Alignment(0, 0),
                )
            ],
            height=self.page_height / 25,
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
        self._initialize_password()

        self._initialize_buttons()
        self._initialize_divider()

        self._initialize_text()

        # all the columns inside of columns inside of columns here is so that the buttons are spaced
        # out correctly from the divider, and the buttons + divider as a whole spaced out from the text fields
        self.login_content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Column(
                        [
                            # this is the "text field" item as a whole
                            ft.Column([
                                self.login_text_container,

                                self.username_container,
                                self.password_container,
                            ]),

                            # this is the buttons + divider item as a whole
                            ft.Column(
                                [
                                    self.login_button,
                                    self.horizontal_button_divider,
                                    self.signup_button,
                                ],
                                # we space out the buttons from the divider
                                spacing=13
                            )
                        ],
                        # we space out the text item from the button/divider item
                        spacing=25,
                    ),
                ],
                spacing=12,
                expand=True
            ),
            width=self.page_width / 3,
            padding=10,
            alignment=ft.Alignment(0, 0)
        )

        self.spaced_content = ft.Column(
            [
                # the empty containers are there for the spacing of the items, so that the login content will be
                # in the middle of the right side.
                ft.Container(height=140, expand=3),
                self.login_content,
                ft.Container(height=180, expand=10, )
            ],
            alignment=ft.MainAxisAlignment.START,
        )

        self.left_side = ft.Container(
            content=self.spaced_content,
            expand=3,
            bgcolor=ft.Colors.WHITE,
            padding=0,
        )

        self.right_side = ft.Container(
            expand=10,
            bgcolor=ft.Colors.BLUE_900,
            padding=0,
        )

        self.page_view = ft.Row(
            controls=[
                self.left_side,
                self.right_side
            ],
            expand=True,
            spacing=0,
        )

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

        self.page_view.controls.append(banner)
        self.page_view.update()

    def _switch_to_signup(self, e):
        # importing SignupPage inside the function so that circular import error doesn't happen.
        # this is because the import only happens when the button is clicked, and not loaded when the page loads initially.
        from GUI.signup import SignupPage

        SignupPage(self.page).show()

    def _send_login(self, e):
        """
        send the login request to the server with the input values from the user.

        endpoint: user/login (POST)

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

        username = self.username_textbox.value

        # passwords are stripped of whitespaces.
        password = self.password_textbox.value.strip()

        # reset any currently showing error so that if they are solved, they wont show anymore
        self.username_textbox.error_text = None
        self.password_textbox.error_text = None

        # we check the length of the password and username before sending it to the server in order to not send useless
        # requests
        if len(password) < 6:
            self.password_textbox.error_text = "password too short"
            self.password_textbox.update()

            return

        if len(username) < 3:
            self.username_textbox.error_text = "username too short"
            self.username_textbox.update()

            return

        if self.transport:
            self.transport.write(
                ClientMessage(
                    authentication=None,
                    endpoint="user/login",
                    method="post",
                    payload={
                        "username": username,
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
    LoginPage(page=page).show()


if __name__ == "__main__":
    ft.app(main, assets_dir="Assets")
