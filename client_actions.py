from asyncio.transports import Transport

import GUI.upload_song
from pseudo_http_protocol import ServerMessage, ClientMessage
from Caches.user_cache import ClientSideUserCache

from encryptions import EncryptedTransport
from DHE.dhe import DHE, generate_dhe_response

import flet as ft
from flet import Page

from gui_testing import MainPage


async def complete_authentication(_: Page, transport: EncryptedTransport, server_message: ServerMessage, __: ClientSideUserCache):
    """
    this function is used to finish transferring the key using dhe.
    it sends the client's public key back to the server.

    this function also saves the IV and full key to the transport

    tied to authentication/key_exchange

    expected payload:
    {
        "base": int,
        "mod": int,
        "public": int,
        "iv": bytes
    }

    expected output:
    {
        "public": str
    }
    """

    payload = server_message.payload

    try:
        dhe_base = payload["base"]
        dhe_mod = payload["mod"]
        server_public_value = payload["public"]

        aes_iv = payload["iv"]
    except KeyError:
        raise # todo: figure out what to do with malformed server messages (likely being faked messages)

    client_dhe: DHE = generate_dhe_response(mod=dhe_mod, base=dhe_base)

    client_public_value = client_dhe.calculate_public()

    transport.write(
        ClientMessage(
            authentication=None,
            method="respond",
            endpoint="authentication/key_exchange",
            payload={
                "public": client_public_value
            }
        ).encode()
    )

    mutual_key_value = client_dhe.calculate_mutual(peer_public_value=server_public_value)

    aes_key = client_dhe.kdf_derive(mutual_key=mutual_key_value, iterations=10000, size=16)

    transport.iv = aes_iv
    transport.key = aes_key


async def user_login(page: Page, transport: EncryptedTransport, server_message: ServerMessage, user_cache: ClientSideUserCache):
    """
    this function expects the login result from requesting a login from the server.
    it then saves the session token and the user ID to the ClientSideUserCache.

    tied to user/login

    expected payload:
    {
        "session_token": str,
        "user_id": str
    }

    expected output:
    None
    """

    payload = server_message.payload

    try:
        session_token = payload["session_token"]
        user_id = payload["user_id"]
    except KeyError:
        raise # todo: figure out what to do with malformed server messages (likely being faked messages)

    user_cache.session_token = session_token
    user_cache.user_id = user_id

    # todo: check why the class isnt updated globally despite classes being mutable
    page.user_cache = user_cache

    # this is a temporary MainPage for testing purposes only
    MainPage(page).start()


async def song_upload_finish(page: Page, transport: EncryptedTransport, server_message: ServerMessage, user_cache: ClientSideUserCache):
    """
    this function is used in order to stop the "uploading" overlay-blocking GUI when the server finishes processing
    all the sent data

    tied to song/upload/finish

    expected payload:
    {
        "success": bool
    }

    expected output:
    None
    """

    payload = server_message.payload

    try:
        success: bool = payload["success"]
    except KeyError:
        raise # todo: figure out what to do with malformed server messages (likely being faked messages)

    if success and hasattr(page, "view"):
        page_view: GUI.upload_song.UploadPage = page.view
        page_view._remove_blocking_overlay()


class DownloadSong:
    def __init__(self):
        self.preview_image_chunks: dict[str, list[tuple[int, str]]] = {}
        """
        dict[
            file_id, tuple[chunk number, b64_chunk]
        ]
        """

    async def download_preview_chunks(self, page: Page, transport: EncryptedTransport, server_message: ServerMessage, user_cache: ClientSideUserCache):
        """
        this function gathers all the preview (cover art) file chunks and combines them in a list to later be shown
        in the GUI

        tied to song/download/preview/file

        expected payload:
        {
            "chunk": str,
            "file_id": str,
            "chunk_number": int,
            "is_last_chunk": bool,
            "song_id": int
        }

        expected output:
        None
        """

        payload = server_message.payload

        try:
            chunk: str = payload["chunk"]
            chunk_number: int = payload["chunk_number"]
            file_id = payload["file_id"]
            song_id = payload["song_id"]
            is_last_chunk: bool = payload["is_last_chunk"]
        except KeyError:
            raise  # todo: figure out what to do with malformed server messages (likely being faked messages)\

        if file_id not in self.preview_image_chunks:
            self.preview_image_chunks[file_id] = [(chunk_number, chunk)]
        else:
            self.preview_image_chunks[file_id].append((chunk_number, chunk))

        if is_last_chunk:
            b64_chunk_list: list[tuple[int, str]] = self.preview_image_chunks[file_id]

            # sorts the chunks to be in the correct order
            b64_chunk_list.sort(key=lambda x: x[0])

            b64_file_bytes = "".join((b64_chunk for chunk_num, b64_chunk in b64_chunk_list))

            page.view.page_view.controls.append(
                ft.Container(
                    ft.Image(
                        src_base64=b64_file_bytes,
                        fit=ft.ImageFit.FILL
                    ),
                    height=500,
                    width=500,
                    bgcolor=ft.Colors.GREY
                )
            )

            page.update()

