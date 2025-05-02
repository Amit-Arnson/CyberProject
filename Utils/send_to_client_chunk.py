import traceback

import asyncio
import base64

import aiofiles

import aiofiles.os as aos

from encryptions import EncryptedTransport
from pseudo_http_protocol import ServerMessage
from Utils.chunk import fast_create_unique_id

import logging

import asqlite
from queries import (
    Music,
    MediaFiles
)


async def send_song_preview_chunks(
        transport: EncryptedTransport,
        db_pool: asqlite.Pool,
        song_ids: list[int]
):
    default_cover_image_path = await aos.path.abspath(r"./Assets/no_cover_art.webp")

    async with db_pool.acquire() as connection:
        # a list of (path, data_dict) tuples based on song ID
        song_path_and_data: list[
            tuple[str, dict[str, str | int | list[str]]]
        ] = await Music.bulk_fetch_song_preview_data(connection=connection, song_ids=song_ids, default_cover_image_path=default_cover_image_path)

    try:
        for song_path, song_dict in song_path_and_data:
            song_id = song_dict["song_id"]
            file_id = fast_create_unique_id(song_id)

            song_data_payload = {
                # int
                "song_id": song_id,
                "song_length": song_dict["song_length"],  # in milliseconds

                # str
                "file_id": file_id,
                "artist_name": song_dict["artist_name"],
                "album_name": song_dict["album_name"],
                "song_name": song_dict["song_name"],

                # list[str]
                "genres": song_dict["genres"]
            }

            transport.write(
                ServerMessage(
                    status={
                        "code": 200,
                        "message": f"initial response for song ID {song_id}"
                    },
                    method="POST",
                    endpoint="song/download/preview",
                    payload=song_data_payload
                ).encode()
            )

            await send_file_chunks(
                transport=transport,
                file_id=file_id,
                song_id=song_id,
                path=song_path,
                endpoint="song/download/preview/file"
            )
    except Exception as e:
        traceback.print_exc()
        raise e


async def resend_file_chunks(
        transport: EncryptedTransport,
        db_pool: asqlite.Pool,
        song_id: int,
        original_file_id: str
):
    default_cover_image_path = await aos.path.abspath(r"./Assets/no_cover_art.webp")

    async with db_pool.acquire() as connection:
        cover_art_path = await MediaFiles.fetch_preview_path(
            connection=connection,
            song_id=song_id,
            default_cover_image_path=default_cover_image_path
        )

    try:
        await send_file_chunks(
            transport=transport,
            file_id=original_file_id,
            song_id=song_id,
            path=cover_art_path,
            endpoint="song/download/preview/file"
        )
    except Exception as e:
        traceback.print_exc()
        raise e


async def send_song_audio_chunks(
    transport: EncryptedTransport,
    db_pool: asqlite.Pool,
    song_id: int,
):
    file_id = fast_create_unique_id(song_id)

    async with db_pool.acquire() as connection:
        audio_path = await MediaFiles.fetch_audio_path(
            connection=connection,
            song_id=song_id,
        )

    try:
        await send_file_chunks(
            transport=transport,
            file_id=file_id,
            song_id=song_id,
            path=audio_path,
            endpoint="song/download/audio"
        )
    except Exception as e:
        traceback.print_exc()
        raise e


async def send_file_chunks(
        transport: EncryptedTransport,
        path: str,
        file_id: str,
        song_id: int,
        endpoint: str,
        chunk_size: int = 30,
):
    """
    :param transport: the Encrypted Transport (which inherits from asyncio.transports.Transport) that represents a
    transport where the client has authenticated with the server.
    :param path: the file's path which you want to send.
    each-other without causing confusion. note: this is not the same file ID as what will be created server side in order
    to save and index the files.
    :param file_id: the "chunk's" file ID, which the client can use to combine the chunks into a real file's bytes
    :param song_id: the song's database ID
    :param chunk_size: the size (in kilobytes) which you want to each chunk to be, must be divisible by 3 for padding-less
    base64 compatibility, default 30.
    :param endpoint: the client-side endpoint which to send the file chunks (POST)
    """
    if not path:
        logging.error(f"missing \"path\" in send_to_client_chunk.send_file_chunks() for song ID {song_id}")
        return

    # changes from a kilobyte amount (such as 16) into an approximate kilobyte value (such as 16000) and not the actual
    # kilobyte value, due to the chunks being turned into base64 beforehand, and they cannot have the base64 padding
    # (unless they are the last chunk, where it is fine for it to have the padding)
    chunk_size: int = chunk_size * 1000

    file_total_size = await aos.path.getsize(path)

    async with aiofiles.open(path, "rb") as file:
        chunk_number = 0

        while True:
            chunk = await file.read(chunk_size)

            if not chunk:
                break

            # this is done because flet's ft.Image() only works with src (which is a file or a link) and src_base64,
            # this means that if i want to use raw bytes, they need to be b64 encoded
            b64_chunk: str = base64.b64encode(chunk).decode()

            is_last_chunk = await file.peek(1) == b""
            chunk_number += 1

            payload = {
                "chunk": b64_chunk,
                "song_id": song_id,
                "file_id": file_id,
                "chunk_number": chunk_number,
                "is_last_chunk": is_last_chunk,
                # "expected_size": file_total_size,
            }

            transport.write(
                ServerMessage(
                    status={
                        "code": 200,
                        "message": "success"
                    },
                    method="POST",
                    endpoint=endpoint,
                    payload=payload
                ).encode()
            )

            await asyncio.sleep(0.025)
