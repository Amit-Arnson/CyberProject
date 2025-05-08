import asyncio
import os

import GUI.upload_song
from pseudo_http_protocol import ServerMessage, ClientMessage
from Caches.user_cache import ClientSideUserCache

from encryptions import EncryptedTransport
from DHE.dhe import DHE, generate_dhe_response

import flet as ft
from flet import Page

from GUI.home_page import HomePage

from RSASigning.public import verify_async, async_rsa_encrypt


async def complete_authentication(
        _: Page,
        transport: EncryptedTransport,
        server_message: ServerMessage,
        __: ClientSideUserCache
):
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
        "iv": bytes,
        "signature": byes
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

        signature = payload["signature"]
    except KeyError:
        raise  # todo: figure out what to do with malformed server messages (likely being faked messages)

    server_ip, server_port = transport.get_extra_info('peername')

    is_message_from_server = await verify_async(server_ip.encode(), signature)

    if not is_message_from_server:
        raise # todo: figure out which error to raise when MITM attack

    client_dhe: DHE = generate_dhe_response(mod=dhe_mod, base=dhe_base)

    client_public_value = client_dhe.calculate_public()

    # this is used for anti-bit flipping. the key is encrypted with the hard-coded RSA public key, and decrypted server
    # side using the hard-coded private key.
    hmac_key = os.urandom(32)

    transport.write(
        ClientMessage(
            authentication=None,
            method="respond",
            endpoint="authentication/key_exchange",
            payload={
                "public": client_public_value,
                "HMAC_key": await async_rsa_encrypt(hmac_key)
            }
        ).encode()
    )

    mutual_key_value = client_dhe.calculate_mutual(peer_public_value=server_public_value)

    aes_key = client_dhe.kdf_derive(mutual_key=mutual_key_value, iterations=10000, size=16)

    transport.iv = aes_iv
    transport.key = aes_key
    transport.hmac_key = hmac_key


async def user_login(
        page: Page,
        transport: EncryptedTransport,
        server_message: ServerMessage,
        user_cache: ClientSideUserCache
):
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
        raise  # todo: figure out what to do with malformed server messages (likely being faked messages)

    user_cache.session_token = session_token
    user_cache.user_id = user_id

    # todo: check why the class isnt updated globally despite classes being mutable
    page.user_cache = user_cache

    # this is a temporary MainPage for testing purposes only
    HomePage(page).show()


async def song_upload_finish(
        page: Page,
        transport: EncryptedTransport,
        server_message: ServerMessage,
        user_cache: ClientSideUserCache
):
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
        raise  # todo: figure out what to do with malformed server messages (likely being faked messages)

    if success and hasattr(page, "view"):
        page_view: GUI.upload_song.UploadPage = page.view
        page_view.remove_blocking_overlay()


class DownloadSong:
    def __init__(self):
        self._lock = asyncio.Lock()

        self.preview_info_completed: set[str] = set()
        """
        a set of all of the preview info payloads that finished processing
        """

    async def download_preview_details(
            self,
            page: Page,
            transport: EncryptedTransport,
            server_message: ServerMessage,
            user_cache: ClientSideUserCache
    ):
        """
        this function gathers all the preview's details (e.g., artist name, song length, etc...) and sends them to the GUI

        tied to song/download/preview/file

        expected payload:
        {
                "song_id": int,
                "file_id": str,
                "artist_name": str,
                "album_name": str,
                "song_name":  str,
                "genres": list[str]
        }

        expected output:
        None
        """

        payload = server_message.payload
        session_token = user_cache.session_token

        try:
            song_id: int = payload["song_id"]
            file_id: str = payload["file_id"]
            artist_name: str = payload["artist_name"]
            album_name: str = payload["album_name"]
            song_name: str = payload["song_name"]
            song_length: int = payload["song_length"]  # in milliseconds
            genres: list[str] = payload["genres"]
        except KeyError:
            raise  # todo: Handle malformed messages appropriately

        if hasattr(page, "view") and isinstance(page.view, HomePage):
            page.view.add_song_info(
                song_id=song_id,
                file_id=file_id,
                artist_name=artist_name,
                album_name=album_name,
                song_name=song_name,
                genres=genres,
                song_length=song_length
            )

        async with self._lock:
            self.preview_info_completed.add(file_id)

        # Timeout loop for resending
        max_retries = 3
        retry_count = 0
        while file_id in self.preview_info_completed:
            await asyncio.sleep(2)

            async with self._lock:
                if file_id not in self.preview_info_completed:
                    break

            if retry_count < max_retries:
                retry_count += 1
                print(f"Resending request for file_id {file_id}, attempt {retry_count}")
                transport.write(
                    ClientMessage(
                        authentication=session_token,
                        method="get",
                        endpoint="song/download/preview/resend",
                        payload={
                            "original_file_id": file_id,
                            "song_id": song_id
                        }
                    ).encode()
                )
            else:
                raise Exception(f"Exceeded maximum retries for file_id {file_id}")

    async def download_preview_chunks(
            self, page: Page,
            _: EncryptedTransport,
            server_message: ServerMessage,
            __: ClientSideUserCache
    ):
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
            raise  # todo: Handle malformed messages appropriately

        # Wait for preview info to be completed
        timeout_count = 20
        while file_id not in self.preview_info_completed:
            timeout_count -= 1
            await asyncio.sleep(1)

            print(f"{timeout_count} -> {file_id} -> #{chunk_number}")

            if timeout_count <= 0:
                raise Exception(f"song ID {song_id} with file ID {file_id} timed out awaiting preview info")

        if hasattr(page, "view") and isinstance(page.view, HomePage):
            page.view.stream_cover_art_chunks(
                song_id=song_id,
                file_id=file_id,
                b64_chunk=chunk,
                is_last_chunk=is_last_chunk
            )

        # Cleanup
        async with self._lock:
            self.preview_info_completed.discard(file_id)


async def buffer_audio(
        page: Page,
        transport: EncryptedTransport,
        server_message: ServerMessage,
        user_cache: ClientSideUserCache
):
    """
    this function is used in order to buffer the song audio chunks in the current audio player

    tied to song/download/audio

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
        raise  # todo: Handle malformed messages appropriately

    if hasattr(page, "view") and isinstance(page.view, HomePage) and page.view.is_viewing_song:
        await page.view.stream_audio_chunks(
            song_id=song_id,
            file_id=file_id,
            b64_chunk=chunk,
            is_last_chunk=is_last_chunk
        )


async def load_sheet_images(
        page: Page,
        transport: EncryptedTransport,
        server_message: ServerMessage,
        user_cache: ClientSideUserCache
):
    """
    this function is used in order to load the sheet image view in the SongView

    tied to song/download/sheet

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
        raise  # todo: Handle malformed messages appropriately

    if hasattr(page, "view") and isinstance(page.view, HomePage) and page.view.is_viewing_song:
        await page.view.stream_sheet_chunks(
            song_id=song_id,
            file_id=file_id,
            b64_chunk=chunk,
            is_last_chunk=is_last_chunk
        )