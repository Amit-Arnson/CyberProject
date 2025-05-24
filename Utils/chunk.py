import enum
import logging
import os

import aiofiles
import asyncio

from encryptions import EncryptedTransport
from pseudo_http_protocol import ClientMessage

from base64 import b64encode
from time import time

KILOBYTE: int = 1024


class FileTypes(enum.Enum):
    SHEET = "sheet"
    COVER = "cover"
    AUDIO = "audio"


def fast_create_unique_id(*args: str | int) -> str:
    """creates a unique ID from the given arguments in a none-secure way (however does not contain repetition)"""
    unique_id = []

    for arg in args:
        arg = str(arg)
        unique_id.append(b64encode(arg.encode()).decode())

    # adds the current time in order to reduce the chance of a collision
    unique_id.append(b64encode(str(time()).encode()).decode())

    # adds random bytes in order to reduce the chance of collision
    unique_id.append(b64encode(os.urandom(8)).decode())

    return "-".join(unique_id)


async def send_chunk(
        transport: EncryptedTransport,
        session_token: str,
        tags: list[str],
        artist_name: str,
        album_name: str,
        song_name: str,
        song_path: str,
        covert_art_path: str,
        image_path_list: list[str] = None,
):
    """
    :params...:

    this function handles all the chunking and sending of the files to the server.
    this uses song/upload (POST) for the initial information, and the chunks go through song/upload/file (POST)
    """
    request_id: str = fast_create_unique_id(artist_name, album_name, song_name, *tags[:4])

    if not song_path:
        raise Exception("song is a required selection")

    song_id: str = fast_create_unique_id("song", request_id)

    cover_art_id = ""
    if covert_art_path:
        cover_art_id: str = fast_create_unique_id("cover_art", request_id)

    # if we don't have any images uploaded, we can set the image_ids to an empty list (to indicate that we had no images uploaded)
    image_ids: list[str] = []

    if image_path_list:
        image_ids = [fast_create_unique_id("image", request_id, image_path.split("\\")[-1]) for image_path in image_path_list]

    # create the initial payload
    payload = {
        "tags": tags,
        "artist_name": artist_name,
        "album_name": album_name,
        "song_name": song_name,
        "song_id": song_id,
        "image_ids": image_ids,
        "cover_art_id": cover_art_id,
        "request_id": request_id
    }

    # writes the initial message, where it gives all the necessary information in order to gather the chunks
    # + additional information about the song
    transport.write(
        ClientMessage(
            authentication=session_token,
            method="POST",
            endpoint="song/upload",
            payload=payload
        ).encode()
    )

    # sends the song
    await send_file_chunks(
        transport=transport,
        session_token=session_token,
        path=song_path,
        file_type=FileTypes.AUDIO,
        file_id=song_id,
        request_id=request_id
    )

    # both cover art and sheet images ARE allowed to be empty.

    # send the cover art image
    await send_file_chunks(
        transport=transport,
        session_token=session_token,
        path=covert_art_path,
        file_type=FileTypes.COVER,
        file_id=cover_art_id,
        request_id=request_id,
    )

    if image_path_list:
        # sends all the images
        for image_path, image_id in zip(image_path_list, image_ids):
            await send_file_chunks(
                transport=transport,
                session_token=session_token,
                path=image_path,
                file_type=FileTypes.SHEET,
                file_id=image_id,
                request_id=request_id
            )

    transport.write(
        ClientMessage(
            authentication=session_token,
            method="POST",
            endpoint="song/upload/finish",
            payload={
                "request_id": request_id
            }
        ).encode()
    )


async def send_file_chunks(
        transport: EncryptedTransport,
        session_token: str,
        path: str,
        file_type: FileTypes | str,
        file_id: str,
        request_id: str,
        chunk_size: int = 32,
):
    """
    :param transport: the Encrypted Transport (which inherits from asyncio.transports.Transport) that represents a 
    transport where the client has authenticated with the server.
    :param session_token: the client authentication token.
    :param path: the file's path which you want to send.
    :param file_type: the type of file that you are chunking. either "image" or "audio".
    :param file_id: the personal ID of the file that is about to be sent. this is in order to group the file chunks with
    each-other without causing confusion. note: this is not the same file ID as what will be created server side in order
    to save and index the files.
    :param request_id: the unique ID of the request. this is used in order to group the chunks later on.
    :param chunk_size: the size (in kilobytes) which you want to each chunk to be, default 32.

    sends to (endpoint): songs/upload/file (POST)
    """
    if not path:
        logging.error(f"missing \"path\" in chunk.send_file_chunks() for file_id {file_id}")
        return

    file_type = file_type.value if isinstance(file_type, FileTypes) else file_type

    if file_type not in ("sheet", "audio", "cover"):
        raise ValueError(f"unknown file type: {file_type}")

    # changes from a kilobyte amount (such as 16) into a kilobyte value (such as 16384)
    chunk_size: int = chunk_size * KILOBYTE

    # file_size: int = len(file)

    # splits the chunks equally based on chunk size
    # for chunk_number, start in enumerate(range(0, file_size, chunk_size)):

    file_total_size = os.path.getsize(path)

    async with aiofiles.open(path, "rb") as file:
        chunk_number = 0

        while True:
            chunk = await file.read(chunk_size)

            print(len(chunk))
            if not chunk:
                break

            is_last_chunk = await file.peek(1) == b""
            chunk_number += 1

            payload = {
                "request_id": request_id,
                "file_type": file_type,
                "file_id": file_id,
                "chunk": chunk,
                "chunk_number": chunk_number,
                "is_last_chunk": is_last_chunk,
                "expected_size": file_total_size,
            }

            transport.write(
                ClientMessage(
                    authentication=session_token,
                    method="POST",
                    endpoint="song/upload/file",
                    payload=payload
                ).encode()
            )

            await asyncio.sleep(0.025)
            