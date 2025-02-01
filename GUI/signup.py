import flet as ft

from encryptions import EncryptedTransport
from Caches.user_cache import ClientSideUserCache

from pseudo_http_protocol import ClientMessage

class SignupPage:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.padding = 0
        self.page.on_resized = self._page_resize
        self.page.theme_mode = ft.ThemeMode.LIGHT

        self.transport: EncryptedTransport | None = None
        if hasattr(page, "transport"):
            self.transport: EncryptedTransport = page.transport

        # the user cache is not needed in signup (since we don't have a session token assigned yet)
        # self.user_cache: ClientSideUserCache | None = None
        # if hasattr(page, "user_cache"):
        #     self.user_cache: ClientSideUserCache = page.user_cache

        self._initialize_controls()

    def _initialize_controls(self):
        self.username_textbox = ft.TextField(
            max_length=20,
            width=self.page.width,
            height=self.page.height / 10,
            label="username",
        )

        self.display_name_textbox = ft.TextField(
            max_length=20,
            width=self.page.width,
            height=self.page.height / 10,
            label="display name",
        )

        self.password_textbot = ft.TextField(
            password=True,
            can_reveal_password=True,
            max_length=20,
            width=self.page.width,
            height=self.page.height / 10,
            label="password"
        )

        self.confirm_password_textbox = ft.TextField(
            password=True,
            can_reveal_password=True,
            max_length=20,
            width=self.page.width,
            height=self.page.height / 10,
            label="confirm password"
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

        self.to_login_button = ft.Button(
            bgcolor=ft.Colors.BLUE,
            content=ft.Text("LOGIN", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            width=self.page.width,
            height=self.page.height / 12,
            on_click=self._switch_to_login
        )

        # the use of a stack here is to lay the Container that has the "or" text on TOP of the divider.
        self.horizontal_button_divider = ft.Stack(
            controls=[
                ft.Divider(
                    thickness=1,
                    color=ft.Colors.GREY,
                ),
                ft.Container(
                    content=ft.Text(
                        "have an account?",
                        color=ft.Colors.GREY,
                        weight=ft.FontWeight.BOLD,
                        size=self.page.height / 46
                    ),
                    bgcolor=self.page.bgcolor if self.page.bgcolor else ft.Colors.WHITE,

                    height=self.page.height / 30,
                    width=self.page.width / 8,

                    alignment=ft.Alignment(0, 0),

                    right=self.page.width / 14,
                    top=-5
                )
            ],
            height=self.page.height / 25,
            width=self.page.width / 3.5
        )

        self.textbox_background_text = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Signup", size=self.page.width / 35),
                    ft.Text("Create your very own Jambox account!", size=self.page.width / 70),
                ],
                spacing=0,
            ),
            height=self.page.height / 6,
            padding=10
        )

        self.textbox_background = ft.Container(
            content=ft.Column(
                controls=[
                    self.textbox_background_text,

                    self.username_textbox,
                    self.display_name_textbox,
                    self.password_textbot,
                    self.confirm_password_textbox,

                    self.signup_button,
                    self.horizontal_button_divider,
                    self.to_login_button,
                ],
                spacing=6,
                expand=True,
                scroll=ft.ScrollMode.HIDDEN
            ),
            width=self.page.width / 3.5,
            expand=True,
            shadow=ft.BoxShadow(
                spread_radius=2,
                blur_radius=5,
                color=ft.Colors.GREY,
            ),
            bgcolor=self.page.bgcolor if self.page.bgcolor else ft.Colors.WHITE,
            padding=10,
            border_radius=5,
        )

        self.logo_header = ft.Container(
            # bgcolor=ft.Colors.BLUE_300,
            content=ft.Image(
                src="/JamBoxLOGO.png",
                fit=ft.ImageFit.COVER,
                width=100,
                height=100,
            ),
            width=self.page.width,
            height=self.page.height / 15,
            alignment=ft.Alignment(-1, 0)
        )

        self.info_bottom = ft.Container(
            width=self.page.width,
            height=self.page.height,
            # bgcolor=ft.Colors.BLUE_300,
        )

        self.page_view = ft.Column(
            controls=[
                self.logo_header,
                self.textbox_background,
                self.info_bottom,
            ],
            horizontal_alignment=ft.CrossAxisAlignment(
                ft.CrossAxisAlignment.CENTER
            ),
            spacing=0
        )

    def _resize_divider(self):
        self.horizontal_button_divider.width = self.page.width / 3.5
        self.horizontal_button_divider.height = self.page.height / 25

        # divider: ft.Divider = self.horizontal_button_divider.controls[0]
        text_container: ft.Container = self.horizontal_button_divider.controls[-1]

        text_container.right = self.page.width / 14
        text_container.width = self.page.width / 8
        text_container.height = self.page.height / 30

        text_container_content: ft.Text = text_container.content

        text_container_content.size = self.page.height / 46

    def _resize_buttons(self):
        self.to_login_button.width = self.page.width
        self.to_login_button.height = self.page.height / 12

        self.signup_button.width = self.page.width
        self.signup_button.height = self.page.height / 12

    def _resize_textbox(self):
        # height doesn't affect the shown height of the box, however it does change the "padding", which makes it look
        # bad when making the screen large.

        self.username_textbox.width = self.page.width
        # self.username_textbox.height = self.page.height / 10

        self.password_textbot.width = self.page.width
        # self.password_textbot.height = self.page.height / 10

    def _resize_textbox_background(self):
        self.textbox_background.width = self.page.width / 3.5

        self.textbox_background_text.height = self.page.height / 6
        login_text: ft.Text = self.textbox_background_text.content.controls[0]
        info_text: ft.Text = self.textbox_background_text.content.controls[-1]

        login_text.size = self.page.width / 35
        info_text.size = self.page.width / 70

    def _resize_header(self):
        self.logo_header.width = self.page.width,
        self.logo_header.height = self.page.height / 15

        jambox_logo: ft.Image = self.logo_header.content
        jambox_logo.width = self.page.width / 12
        jambox_logo.height = self.page.width / 12

    def _resize_bottom(self):
        self.info_bottom.height = self.page.height
        self.info_bottom.width = self.page.width

    def _resize(self):
        self._resize_bottom()
        self._resize_header()
        self._resize_textbox()
        self._resize_textbox_background()
        self._resize_buttons()
        self._resize_divider()

    def _page_resize(self, e):
        self._resize()
        self.page.update()

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

        if password != confirm_password:
            self.confirm_password_textbox.error_text = "password does not match up!"
            self.confirm_password_textbox.update()

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

    def show(self, clear: bool = True):
        """:param clear: whether to clear the page before trying to add the page's content or not."""

        if clear:
            self.page.clean()

        self.page.add(self.page_view)

        self.page.update()


def main(page: ft.Page):
    SignupPage(page=page).show()


if __name__ == "__main__":
    ft.app(main, assets_dir="Assets")
