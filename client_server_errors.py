# this is where all the "error" endpoints will point

from pseudo_http_protocol import ServerMessage
from Caches.user_cache import ClientSideUserCache

from encryptions import EncryptedTransport

import flet as ft
from flet import Page


async def login_error(page: Page, _: EncryptedTransport, server_message: ServerMessage, __: ClientSideUserCache):
    """
    this function is used to visually display that an error occurred when trying to log in.

    tied to user/login/error

    expected payload:
    {
        ???
    }

    expected output:
    None

    expected page location:
    LoginPage
    """

    status_code = server_message.status.get("code")
    status_message = server_message.status.get("message")

    # since the .show() method applies "self" to page.view, we can access the page's contents and controls (which are
    # normally saved in the self of LoginPage) by accessing page.view

    if hasattr(page, "view"):
        login_page = page.view

        # todo: check if i want to make it so that instead of directly changing the "self" values, ill have a helper function inbetween to make things more controlled
        login_page.username_textbox.error_text = status_message
        login_page.username_textbox.update()
    else:
        # whilst page.view may not exist in some cases, page.server_error is always defined at the start of runtime.
        # this means that we can always access it.
        page.server_error(
            ft.Text(
                f"{status_message}\n\nstatus: {status_code}"
            )
        )
