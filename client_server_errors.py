# this is where all the "error" endpoints will point
import asyncio

import GUI.upload_song
from pseudo_http_protocol import ServerMessage
from Caches.user_cache import ClientSideUserCache

from encryptions import EncryptedTransport

import flet as ft
from flet import Page


def remove_upload_page_blocking_overplay(page: Page):
    if hasattr(page, "view") and isinstance(page.view, GUI.upload_song.UploadPage):
        page.view.remove_blocking_overlay()


async def pre_message_error(page: Page, _: EncryptedTransport, server_message: ServerMessage, __: ClientSideUserCache):
    status_code = server_message.status.get("code")
    status_message = server_message.status.get("message")

    page.server_error(
        ft.Text(
            f"{status_message}\n\nstatus: {status_code}"
        )
    )


async def login_error(page: Page, _: EncryptedTransport, server_message: ServerMessage, __: ClientSideUserCache):
    """
    this function is used to visually display that an error occurred when trying to log in.

    tied to user/login/error

    expected payload:
    {
        "type": str
    }

    expected output:
    None

    expected page location:
    LoginPage
    """

    status_code = server_message.status.get("code")
    status_message = server_message.status.get("message")
    extra = server_message.payload

    # since the .show() method applies "self" to page.view, we can access the page's contents and controls (which are
    # normally saved in the self of LoginPage) by accessing page.view

    if hasattr(page, "view"):
        login_page = page.view

        error_type = extra.get("type")

        if error_type == "password":
            login_page.password_textbox.error_text = status_message
        else:
            login_page.username_textbox.error_text = status_message

        page.update()
    else:
        # whilst page.view may not exist in some cases, page.server_error is always defined at the start of runtime.
        # this means that we can always access it.
        page.server_error(
            ft.Text(
                f"{status_message}\n\nstatus: {status_code}"
            )
        )


async def signup_error(page: Page, _: EncryptedTransport, server_message: ServerMessage, __: ClientSideUserCache):
    """
    this function is used to visually display that an error occurred when trying to sign up to create a new account.

    tied to user/signup/login/error

    (this is tied to user/signup/login and not use user/signup because in the GUI it will also try to instantly log the user
    in, this means that user/signup is never actually called as a stand-alone in the GUI)

    expected payload:
    {
        "type": str
    }

    expected output:
    None

    expected page location:
    SignupPage
    """

    status_code = server_message.status.get("code")
    status_message = server_message.status.get("message")
    extra = server_message.payload

    # since the .show() method applies "self" to page.view, we can access the page's contents and controls (which are
    # normally saved in the self of the class) by accessing page.view

    if hasattr(page, "view"):
        signup_page = page.view

        error_type = extra.get("type")

        if error_type == "password":
            signup_page.password_textbox.error_text = status_message
        elif error_type == "display_name":
            signup_page.display_name_textbox.error_text = status_message
        else:
            signup_page.username_textbox.error_text = status_message

        page.update()
    else:
        # whilst page.view may not exist in some cases, page.server_error is always defined at the start of runtime.
        # this means that we can always access it.
        page.server_error(
            ft.Text(
                f"{status_message}\n\nstatus: {status_code}"
            )
        )


async def song_upload_error(page: Page, _: EncryptedTransport, server_message: ServerMessage, __: ClientSideUserCache):
    """
    this function is used to visually display error information when uploading invalid information, and is also used
    to stop the "upload chunks" task tied to the class

    tied to song/upload/error

    expected payload:
    {
        "type": str
    }

    expected output:
    None

    expected page location:
    UploadSong
    """

    status_code = server_message.status.get("code")
    status_message = server_message.status.get("message")
    extra = server_message.payload

    # since the .show() method applies "self" to page.view, we can access the page's contents and controls (which are
    # normally saved in the self of the class) by accessing page.view

    remove_upload_page_blocking_overplay(page=page)

    if hasattr(page, "view"):
        upload_page: GUI.upload_song.UploadPage = page.view

        if hasattr(upload_page, "send_chunks_task"):
            send_chunks_task: asyncio.Task = upload_page.send_chunks_task

            send_chunks_task.cancel()

    page.server_error(
        ft.Text(
            f"{status_message}\n\nstatus: {status_code}"
        )
    )

