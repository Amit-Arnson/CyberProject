import flet as ft

from encryptions import EncryptedTransport
from Caches.user_cache import ClientSideUserCache

from GUI.Controls.navigation_sidebar import NavigationSidebar

from pseudo_http_protocol import ClientMessage


# todo: add the logo somewhere? idk
class LoginPage:
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

        # this holds the session token (which is the authentication)
        self.user_cache: ClientSideUserCache | None = None
        if hasattr(page, "user_cache"):
            self.user_cache: ClientSideUserCache = page.user_cache

        self.sidebar = NavigationSidebar(page=page)
        self.sidebar.expand = 2

        self._initialize_controls()

    def _initialize_controls(self):
        self.page_view = ft.Row(
            [
                self.sidebar,
                ft.Container(expand=7)
            ],
            expand=10,
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
    LoginPage(page=page).show()


if __name__ == "__main__":
    ft.app(main, assets_dir="Assets")
