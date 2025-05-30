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
from GUI.tempo_finder import AudioInformation
from GUI.settings import Settings

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
        raise Exception("invalid message sent from server. this is likely a hacking attempt")

    server_ip, server_port = transport.get_extra_info('peername')

    is_message_from_server = await verify_async(server_ip.encode(), signature)

    if not is_message_from_server:
        raise Exception("invalid message sent from server. this is likely a hacking attempt")

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
        "user_id": str,
        "username": str,
        "display_name": str
    }

    expected output:
    None
    """

    payload = server_message.payload

    try:
        session_token = payload["session_token"]
        user_id = payload["user_id"]
        username = payload["username"]
        display_name = payload["display_name"]
    except KeyError:
        raise Exception("invalid message sent from server. this is likely a hacking attempt")

    user_cache.session_token = session_token
    user_cache.user_id = user_id
    user_cache.username = username
    user_cache.display_name = display_name

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
        raise Exception("invalid message sent from server. this is likely a hacking attempt")

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

        tied to song/download/preview

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
            user_id: str = payload["user_id"]
            file_id: str = payload["file_id"]
            artist_name: str = payload["artist_name"]
            album_name: str = payload["album_name"]
            song_name: str = payload["song_name"]
            song_length: int = payload["song_length"]  # in milliseconds
            genres: list[str] = payload["genres"]
            is_favorite_song: bool = payload["is_favorite_song"]
        except KeyError:
            raise Exception("invalid message sent from server. this is likely a hacking attempt")

        if hasattr(page, "view") and isinstance(page.view, HomePage):
            page.view.add_song_info(
                song_id=song_id,
                user_id=user_id,
                file_id=file_id,
                artist_name=artist_name,
                album_name=album_name,
                song_name=song_name,
                genres=genres,
                song_length=song_length,
                is_favorite_song=is_favorite_song
            )

        async with self._lock:
            self.preview_info_completed.add(file_id)

        # sometimes the song image does not arrive as expected, this is mainly caused by client-side lag. this can be fixed
        # by requesting the image from the server if we notice that it doesnt arrive at a reasonable time

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
            raise Exception("invalid message sent from server. this is likely a hacking attempt")

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
        raise Exception("invalid message sent from server. this is likely a hacking attempt")

    if hasattr(page, "view") and isinstance(page.view, HomePage) and page.view.is_viewing_song:
        await page.view.stream_audio_chunks(
            song_id=song_id,
            file_id=file_id,
            b64_chunk=chunk,
            is_last_chunk=is_last_chunk
        )
    elif hasattr(page, "view") and isinstance(page.view, AudioInformation):
        await page.view.add_song_bytes(
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
        raise Exception("invalid message sent from server. this is likely a hacking attempt")

    if hasattr(page, "view") and isinstance(page.view, HomePage) and page.view.is_viewing_song:
        await page.view.stream_sheet_chunks(
            song_id=song_id,
            file_id=file_id,
            b64_chunk=chunk,
            is_last_chunk=is_last_chunk
        )


async def load_genre_browser(
        page: Page,
        transport: EncryptedTransport,
        server_message: ServerMessage,
        user_cache: ClientSideUserCache
):
    """
    this function is used in order to load the genre list

    tied to song/genres

    expected payload:
    {
        "genres": list[str]
    }

    expected output:
    None
    """

    payload = server_message.payload

    try:
        genres: list[str] = payload["genres"]
    except KeyError:
        raise Exception("invalid message sent from server. this is likely a hacking attempt")

    if hasattr(page, "view") and isinstance(page.view, HomePage):
        await page.view.add_genres_browse(
            genres=genres
        )


async def load_song_comments(
        page: Page,
        transport: EncryptedTransport,
        server_message: ServerMessage,
        user_cache: ClientSideUserCache
):
    """
    this function is used in order to load song's comments

    tied to song/comments

    expected payload:
    {
        "comments": list[
            {
                "comment_id": int,
                "text": str,
                "uploaded_at": int,
                "uploaded_by": str,
                "uploaded_by_display": str
            }
        ],
        "ai_summary": str
    }

    expected output:
    None
    """

    payload = server_message.payload

    try:
        comments: list[dict] = payload["comments"]
        ai_summary: str = payload["ai_summary"]
    except KeyError:
        raise Exception("invalid message sent from server. this is likely a hacking attempt")

    if hasattr(page, "view") and isinstance(page.view, HomePage):
        await page.view.add_song_comments(
            comments=comments,
            ai_summary=ai_summary
        )


async def upload_song_search_info(
        page: Page,
        transport: EncryptedTransport,
        server_message: ServerMessage,
        user_cache: ClientSideUserCache
):
    """
    this function is used in order to add search results to the searchbar

    tied to song/search

    expected payload:
    {
        "songs": list[
            {"name": str, "artist": str, "album": str, "song_id": int}
        ]
    }

    expected output:
    None
    """

    payload = server_message.payload

    try:
        songs: list[dict[str, str]] = payload["songs"]
    except KeyError:
        raise Exception("invalid message sent from server. this is likely a hacking attempt")

    if hasattr(page, "view") and isinstance(page.view, AudioInformation):
        page.view.add_search_results(
            songs=songs
        )


async def upload_user_statistics(
        page: Page,
        transport: EncryptedTransport,
        server_message: ServerMessage,
        user_cache: ClientSideUserCache
):
    """
    this function is used in order to add the user statistics to the settings page

    tied to user/statistics

    expected payload:
    {
        "total_song_uploads": int,
        "total_comments": int
    }

    expected output:
    None
    """

    payload = server_message.payload

    try:
        total_song_uploads: int = payload["total_song_uploads"]
        total_comments: int = payload["total_comments"]
    except KeyError:
        raise Exception("invalid message sent from server. this is likely a hacking attempt")

    if hasattr(page, "view") and isinstance(page.view, Settings):
        page.view.upload_statistics(
            total_song_uploads=total_song_uploads,
            total_comments=total_comments
        )


def user_logout(page: Page):
    """
    this function logs the user out in both client and server

    tied to user/logout

    expected payload:
    None

    expected output:
    None
    """

    from GUI.login import LoginPage

    transport = page.transport
    user_cache = page.user_cache

    transport.write(
        ClientMessage(
            authentication=user_cache.session_token,
            method="post",
            endpoint="user/logout",
            payload={"_no_payload": True}
        ).encode()
    )

    user_cache.user_id = None
    user_cache.display_name = None
    user_cache.session_token = None
    user_cache.username = None

    page.user_cache = user_cache

    LoginPage(page).show()

