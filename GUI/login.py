import flet as ft


class LoginPage:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.on_resized = self._page_resize

        self.username_textbox = ft.TextField(
            max_length=20,
            width=self.page.width / 5,
            height=self.page.height / 10,
        )

        self.password_textbot = ft.TextField(
            password=True,
            can_reveal_password=True,
            max_length=20,
            width=self.page.width / 5,
            height=self.page.height / 10,
        )

        self.textbox_background = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Login", size=25),
                    ft.Text("Log into your JamBox account!", size=10),
                    self.username_textbox,
                    self.password_textbot,
                ]
            ),
            width=self.page.width / 3.5,
            height=self.page.height / 1.5,
            shadow=ft.BoxShadow(
                spread_radius=2,
                blur_radius=5,
                color=ft.Colors.GREY
            ),
            bgcolor=self.page.bgcolor if self.page.bgcolor else ft.Colors.WHITE,
            padding=10,
        )

        self.logo_header = ft.Container(
            width=self.page.width,
            height=self.page.height/10,
            bgcolor=ft.Colors.BLUE_300
        )

        self.info_bottom = ft.Container(
            width=self.page.width,
            height=self.page.height,
            bgcolor=ft.Colors.BLUE_300,
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
            spacing=20
        )

    def _resize_textbox(self):
        self.username_textbox.width = self.page.width / 5
        self.username_textbox.height = self.page.height / 10

        self.password_textbot.width = self.page.width / 5
        self.password_textbot.height = self.page.height / 10

    def _resize_textbox_background(self):
        self.textbox_background.width = self.page.width / 3.5
        self.textbox_background.height = self.page.height / 1.5

    def _resize_header(self):
        self.logo_header.width = self.page.width,
        self.logo_header.height = self.page.height / 10

    def _resize_bottom(self):
        self.info_bottom.height = self.page.height
        self.info_bottom.width = self.page.width

    def _resize(self):
        self._resize_bottom()
        self._resize_header()
        self._resize_textbox()
        self._resize_textbox_background()

    def _page_resize(self, e):
        self._resize()
        self.page.update()

    def show(self):
        self.page.padding = 0
        self.page.add(self.page_view)

        self.page.update()

def main(page: ft.Page):
    LoginPage(page=page).show()


if __name__ == "__main__":
    ft.app(main)