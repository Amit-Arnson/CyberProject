import enum
import os

from encryptions import EncryptedTransport
from pseudo_http_protocol import ClientMessage

from base64 import b64encode
from time import time

KILOBYTE: int = 1024


class FileTypes(enum.Enum):
    IMAGE = "image",
    AUDIO = "audio"


def fast_create_unique_id(*args: str) -> str:
    """creates a unique ID from the given arguments in a none-secure way (however does not contain repetition)"""
    unique_id = []

    for arg in args:
        unique_id.append(b64encode(arg).decode())

    # adds the current time in order to reduce the chance of a collision
    unique_id.append(b64encode(time().hex()).decode())

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
        song_bytes: bytes,
        image_bytes_list: list[bytes],
):
    # todo: describe params
    """
    :params...:

    this function handles all the chunking and sending of the files to the server.
    this uses song/upload (POST) for the initial information, and the chunks go through song/upload/file (POST)
    """
    request_id: str = fast_create_unique_id(artist_name, album_name, song_name, *tags[:4])

    song_id: str = fast_create_unique_id("song", request_id)

    image_ids: list[str] = [fast_create_unique_id("image", request_id)]

    # create the initial payload
    payload = {
        "tags": tags,
        "artist_name": artist_name,
        "album_name": album_name,
        "song_name": song_name,
        "song_id": song_id,
        "image_ids": image_ids,
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
        file=song_bytes,
        file_type=FileTypes.AUDIO,
        file_id=song_id,
        request_id=request_id
    )

    # sends all of the images
    for image_bytes, image_id in zip(image_bytes_list, image_ids):
        await send_file_chunks(
            transport=transport,
            session_token=session_token,
            file=image_bytes,
            file_type=FileTypes.IMAGE,
            file_id=image_id,
            request_id=request_id
        )


# todo: check if this function actually needs to be async
async def send_file_chunks(
        transport: EncryptedTransport,
        session_token: str,
        file: bytes,
        file_type: FileTypes | str,
        file_id: str,
        request_id: str,
        chunk_size: int = 16,
):
    """
    :param transport: the Encrypted Transport (which inherits from asyncio.transports.Transport) that represents a 
    transport where the client has authenticated with the server.
    :param session_token: the client authentication token.
    :param file: the file's bytes which you want to send.
    :param file_type: the type of file that you are chunking. either "image" or "audio".
    :param file_id: the personal ID of the file that is about to be sent. this is in order to group the file chunks with
    each-other without causing confusion. note: this is not the same file ID as what will be created server side in order
    to save and index the files.
    :param request_id: the unique ID of the request. this is used in order to group the chunks later on.
    :param chunk_size: the size (in kilobytes) which you want to each chunk to be, default 16.
    
    sends to (endpoint): songs/upload/file (POST)
    """

    if file_type not in ("image", "audio"):
        raise ValueError(f"unknown file type: {file_type}")

    # changes from a kilobyte amount (such as 16) into a kilobyte value (such as 16384)
    chunk_size: int = chunk_size * KILOBYTE

    file_size: int = len(file)

    # splits the chunks equally based on chunk size
    for chunk_number, start in enumerate(range(0, file_size, chunk_size)):
        chunk = file[start:start + chunk_size]

        payload = {
            "request_id": request_id,
            "file_type": file_type,
            "file_id": file_id,
            "chunk": chunk,
            "chunk_number": chunk_number
        }

        transport.write(
            ClientMessage(
                authentication=session_token,
                method="POST",
                endpoint="song/upload/file",
                payload=payload
            ).encode()
        )
