import logging
import os

import bisect
import traceback

import asyncio

from pseudo_http_protocol import ClientMessage, ServerMessage
from Caches.client_cache import ClientPackage
from Caches.user_cache import UserCache, UserCacheItem

from AES_128 import cbc
from DHE.dhe import DHE

from FileSystem.base_file_system import System, FileChunk

import asqlite

from secure_user_credentials import (
    generate_hashed_password,
    authenticate_password,
    generate_user_id,
    generate_session_token
)

import queries
from queries import (
    FileSystem,
    MediaFiles,
    Music,
    MusicSearch
)

from Compress.audio import get_audio_length
from Utils.send_to_client_chunk import send_song_preview_chunks

from Errors.raised_errors import (
    NoEncryption,
    InvalidCredentials,
    TooLong,
    UserExists,
    InvalidPayload,
    TooShort,
    InvalidDataType
)


async def authenticate_client(_: asqlite.Pool, client_package: ClientPackage, client_message: ClientMessage,
                              user_cache: UserCache):
    """
    this function is used to finish transferring the key using dhe.

    this function is tied to authentication/key_exchange (RESPOND)

    expected payload:
    {
        "public": int
    }

    expected output: no message sent (none)

    expected cache pre-function:
    > address
    > iv

    expected cache post-function:
    > address
    > iv
    + aes_key
    """

    client = client_package.client
    address = client_package.address

    # gets the UserCacheItem for this specific client (and references it)
    client_user_cache: UserCacheItem = user_cache[address]

    payload = client_message.payload

    try:
        client_public_value = payload["public"]
    except KeyError:
        payload_keys = " ".join(f"\"{key}\"" for key in payload.keys())
        raise InvalidPayload(f"Invalid payload passed. expected key \"public\", instead got {payload_keys}")

    server_dhe = DHE(
        e=client_user_cache.dhe_exponent,
        g=client_user_cache.dhe_base,
        p=client_user_cache.dhe_mod
    )

    # todo: figure out how to stop fake base/mod in DHE (since they can be spoofed client side)

    # calculates the mutual key (note: this key is a secret key and should not be shared)
    mutual_key_number: int = server_dhe.calculate_mutual(client_public_value)

    # derives a 16 byte key from the mutual key
    aes_key = server_dhe.kdf_derive(mutual_key=mutual_key_number, iterations=10000, size=16)

    # adds the derived key to the global user cache
    client_user_cache.aes_key = aes_key

    # adding the key to the EncryptedTransport
    client.key = aes_key

    # this is just for testing. will remove later

    # print(f"ckiv: {client.key, client.iv}")
    # client.write(ServerMessage(
    #         status={
    #             "code": 000,
    #             "message": "encryption key exchange"
    #         },
    #         method="initiate",
    #         endpoint="key_exchange",
    #         payload={
    #             "testing": True
    #         }
    #     ).encode())


async def user_signup_and_login(db_pool: asqlite.Pool, client_package: ClientPackage, client_message: ClientMessage,
                                user_cache: UserCache):
    """
    this function is used to create a new user account, and automatically logs the user in

    this function is tied to users/signup/login (POST)

    expected payload:
    {
        "username": str,
        "password": str,
        "display_name": str
    }

    expected output:
    {
        "session_token": str,
        "user_id": str,
    }

    expected cache pre-function:
    > address
    > iv
    > aes_key

    expected cache post-function:
    > address
    > iv
    > aes_key
    + user_id
    + session token
    """

    client = client_package.client
    address = client_package.address

    # checks if the client has completed the key exchange
    if not client.key or not client.iv:
        raise NoEncryption("missing encryption values: please re-authenticate")

    client_user_cache: UserCacheItem = user_cache[address]
    payload = client_message.payload

    try:
        username = payload["username"]
        password = payload["password"]
        display_name = payload["display_name"]
    except KeyError:
        payload_keys = " ".join(f"\"{key}\"" for key in payload.keys())
        raise InvalidPayload(
            f"Invalid payload passed. expected keys \"username\", \"passwor\", \"display_name\", instead got {payload_keys}")

    hashed_password, salt = generate_hashed_password(password=password)
    user_id = generate_user_id(username=username)

    # username, display name and password length check.

    # checks if it's too long
    if len(username) > 20:
        raise TooLong("Username provided is too long: max 20 characters", extra={"type": "username"})
    elif len(display_name) > 20:
        raise TooLong("Display name provided is too long: max 20 characters", extra={"type": "display_name"})
    elif len(password) > 30:
        raise TooLong("Password is too long: max 30 characters", extra={"type": "password"})

    # checks if it's too short
    if len(username) < 3:
        raise TooShort("Username provided is too short: min 3 characters", extra={"type": "username"})
    elif len(display_name) < 3:
        raise TooShort("Display name provided is too short: min 3 characters", extra={"type": "display_name"})
    elif len(password) < 6:
        raise TooLong("Password is too short: min 6 characters", extra={"type": "password"})

    # creates the user based on the client's input
    async with db_pool.acquire() as connection:
        # using a transaction since im creating 2 queries that rely on each other
        async with connection.transaction():
            # making sure that the user doesn't already exist
            user_exists = await queries.User.user_exists(connection=connection, username=username)

            if user_exists:
                raise UserExists("A user with the given username already exists")

            await queries.User.create_user(
                connection=connection,
                user_id=user_id,
                username=username,
                display_name=display_name,
                password=hashed_password,
                salt=salt
            )

    # now the LOGIN process begins

    user_session_token = generate_session_token(user_id)

    # adding the user ID and session token to the client cache
    client_user_cache.user_id = user_id
    client_user_cache.session_token = user_session_token

    # sends the client the session token and the user ID
    client.write(
        ServerMessage(
            status={
                "code": 200,
                "message": "success"
            },
            method="respond",
            endpoint="user/login",
            payload={
                "session_token": user_session_token,
                "user_id": user_id,
            }
        ).encode()
    )


async def user_signup(db_pool: asqlite.Pool, client_package: ClientPackage, client_message: ClientMessage,
                      _: UserCache):
    """
    this function is used to create a new user account, however it does NOT automatically log the user in (for now, may change)

    this function is tied to users/signup (POST)

    expected payload:
    {
        "username": str,
        "password": str,
        "display_name": str
    }

    expected output:
    {
        "user_id": str,
    }

    expected cache pre-function:
    > address
    > iv
    > aes_key

    expected cache post-function:
    > address
    > iv
    > aes_key
    """

    client = client_package.client

    # checks if the client has completed the key exchange
    if not client.key or not client.iv:
        raise NoEncryption("missing encryption values: please re-authenticate")

    payload = client_message.payload

    try:
        username = payload["username"]
        password = payload["password"]
        display_name = payload["display_name"]
    except KeyError:
        payload_keys = " ".join(f"\"{key}\"" for key in payload.keys())
        raise InvalidPayload(
            f"Invalid payload passed. expected keys \"username\", \"passwor\", \"display_name\", instead got {payload_keys}")

    hashed_password, salt = generate_hashed_password(password=password)
    user_id = generate_user_id(username=username)

    # username, display name and password length check.

    # checks if it's too long
    if len(username) > 20:
        raise TooLong("Username provided is too long: max 20 characters", extra={"type": "username"})
    elif len(display_name) > 20:
        raise TooLong("Display name provided is too long: max 20 characters", extra={"type": "display_name"})
    elif len(password) > 30:
        raise TooLong("Password is too long: max 30 characters", extra={"type": "password"})

    # checks if it's too short
    if len(username) < 3:
        raise TooShort("Username provided is too short: min 3 characters", extra={"type": "username"})
    elif len(display_name) < 3:
        raise TooShort("Display name provided is too short: min 3 characters", extra={"type": "display_name"})
    elif len(password) < 6:
        raise TooLong("Password is too short: min 6 characters", extra={"type": "password"})

    # creates the user based on the client's input
    async with db_pool.acquire() as connection:
        # using a transaction since im creating 2 queries that rely on each other
        async with connection.transaction():
            # making sure that the user doesn't already exist
            user_exists = await queries.User.user_exists(connection=connection, username=username)

            if user_exists:
                raise UserExists("A user with the given username already exists")

            await queries.User.create_user(
                connection=connection,
                user_id=user_id,
                username=username,
                display_name=display_name,
                password=hashed_password,
                salt=salt
            )

    # sends a message to the client to show that the account creation was successful and sends the user ID to the client
    client.write(
        ServerMessage(
            status={
                "code": 200,
                "message": "success"
            },
            method="respond",
            endpoint="user/signup",
            payload={
                "user_id": user_id,
            }
        ).encode()
    )


async def user_login(db_pool: asqlite.Pool, client_package: ClientPackage, client_message: ClientMessage,
                     user_cache: UserCache):
    """
    this function is used to log a user in, by accepting a password and username (then checking that they are valid)
    and generating a session token and returns the user id.

    this function is tied to user/login (POST)

    expected payload:
    {
        "username": str,
        "password": str
    }

    expected output:
    {
        "session_token": str,
        "user_id": str,
    }

    expected cache pre-function:
    > address
    > iv
    > aes_key

    expected cache post-function:
    > address
    > iv
    > aes_key
    + user_id
    + session token
    """

    client = client_package.client
    address = client_package.address

    # checks if the client has completed the key exchange
    if not client.key or not client.iv:
        raise NoEncryption("missing encryption values: please re-authenticate")

    # gets the UserCacheItem for this specific client (and references it)
    client_user_cache: UserCacheItem = user_cache[address]

    payload = client_message.payload

    try:
        username = payload["username"]
        password = payload["password"]
    except KeyError:
        payload_keys = " ".join(f"\"{key}\"" for key in payload.keys())
        raise InvalidPayload(
            f"Invalid payload passed. expected key \"username\", \"password\", instead got {payload_keys}")

    async with db_pool.acquire() as connection:
        user = await queries.User.fetch_user(
            connection=connection,
            username=username,
        )

    if not user:
        raise InvalidCredentials("user doesnt exist")

    hashed_password: str = user["password"]
    salt: bytes = user["salt"]

    if not authenticate_password(password=password, hashed_password=hashed_password, salt=salt):
        raise InvalidCredentials("Invalid login credentials passed")

    user_id: str = user["user_id"]

    user_session_token = generate_session_token(user_id)

    # adding the user ID and session token to the client cache
    client_user_cache.user_id = user_id
    client_user_cache.session_token = user_session_token

    # sends the client the session token and the user ID
    client.write(
        ServerMessage(
            status={
                "code": 200,
                "message": "success"
            },
            method="respond",
            endpoint="user/login",
            payload={
                "session_token": user_session_token,
                "user_id": user_id,
            }
        ).encode()
    )


class UploadSong:
    def __init__(self):
        # to prevent any data corruption/race conditions
        self._lock = asyncio.Lock()

        # gotten from song/upload
        # dict[
        #     request_id, dict[
        #                 "user_id": str
        #                 "tags": list[str],
        #                 "artist_name": str,
        #                 "album_name": str,
        #                 "song_name": str,
        #                 "song_id": str,
        #                 "cover_art_id": str,
        #                 "image_ids": list[str],
        #     ]
        # ]
        self.song_information: dict[
            str, dict[str, str | list[str]]
        ] = {}

        # gotten from song/upload/file
        # dict[
        #     tuple[request_id, file_id]: dict[
        #                                 "user_id": str
        #                                 "chunks": list[bytes],
        #                                 "current_size": int,
        #                                 "chunk_number": int,
        #                                 "file_type": str ("image" or "audio")
        #     ]
        # ]
        # self.chunk_files: dict[
        #     tuple[str, str], dict[str, list[bytes] | int | str]
        # ] = {}

        # dict[
        #     tuple[request_id, file_id],
        #     dict[
        #         "paths": tuple[(actual) file_id, cluster_id, save_directory],
        #         "current_size": int,
        #         "file_extension": str,
        #         "previous_chunk": int,
        #         "lock": asyncio.Lock,
        #     ]
        # ]
        self.file_save_ids: dict[
            tuple[str, str], dict[str, tuple[str, str, str] | int | str | asyncio.Lock]
        ] = {}

        """
        dict[
            tuple[request_id, file_id],
            dict[
                "cluster_id": str,
                "file_id": str,
                "user_uploaded_id": str,
                "size": int,
                "raw_file_id": str,
                "file_format": str
            ]
        ]
        """
        self.base_file_parameters: dict[
            tuple[str, str], dict[
                str, str | int
            ]
        ] = {}

        """
        dict[
            tuple[request_id, file_id],
            full file path (save_dir/cluster/file.extension)
        ]
        """
        self.base_file_paths: dict[
            tuple[str, str], str
        ] = {}

        """
        dict[
            request_id,
            set[file_id]
        ]
        """
        self.base_file_set: dict[str, set[str]] = {}

        # dict[request_id, file_id] -> list[(chunk number, chunk bytes), ...]
        self.out_of_order_chunks: dict[tuple[str, str], list[tuple[int, bytes]]] = {}

    async def upload_song(
            self,
            _: asqlite.Pool,
            client_package: ClientPackage,
            client_message: ClientMessage,
            user_cache: UserCache
    ):
        """
        this function is used in order to upload file INFORMATION (not bytes). this function also gathers all the
        file_ids that are to-be-sent in order to organize and combine the chunks later

        this function is tied to song/upload (POST)

        expected payload:
        {
            "tags": list[str],
            "artist_name": str,
            "album_name": str,
            "song_name": str,
            "song_id": str,
            "cover_art_id": str,
            "image_ids": list[str],
            "request_id": str
        }

        expected output:
        None

        expected cache pre-function:
        > address
        > iv
        > aes_key
        > user_id
        > session_token

        expected cache post-function:
        > address
        > iv
        > aes_key
        > user_id
        > session_token
        """

        client = client_package.client
        address = client_package.address

        # checks if the client has completed the key exchange
        if not client.key or not client.iv:
            raise NoEncryption("missing encryption values: please re-authenticate")

        client_user_cache: UserCacheItem = user_cache[address]
        user_id: str = client_user_cache.user_id

        payload = client_message.payload

        try:
            tags: list[str] = payload["tags"]
            artist_name: str = payload["artist_name"]
            album_name: str = payload["album_name"]
            song_name: str = payload["song_name"]
            song_id: str = payload["song_id"]
            cover_art_id: str = payload["cover_art_id"]
            image_ids: list[str] = payload["image_ids"]
            request_id: str = payload["request_id"]
        except KeyError:
            payload_keys = " ".join(f"\"{key}\"" for key in payload.keys())
            raise InvalidPayload(
                f"Invalid payload passed. expected keys \"tags\", \"artist_name\", \"album_name\", \"song_name\", "
                f"\"song_id\", \"cover_art_id\", \"image_ids\", \"request_id\", instead got {payload_keys}")

        # checks for "too long" type inputs (too many items in a list or name too long)
        if len(tags) > 5:
            raise TooLong("too many tags given. maximum amount possible is 5", extra={"type": "tags"})
        elif len(artist_name) > 100:
            raise TooLong("artist name too long, must be shorter than 100 characters", extra={"type": "artist"})
        elif len(album_name) > 100:
            raise TooLong("album name too long, must be shorter than 100 characters", extra={"type": "album"})
        elif len(song_name) > 100:
            raise TooLong("artist name too long, must be shorter than 100 characters", extra={"type": "song"})

        # checks for too short
        if len(tags) < 1:
            raise TooShort("not enough tags given. minimum amount possible is 1", extra={"type": "tags"})
        elif len(artist_name) < 1:
            raise TooShort("artist name too short, must be longer than 1 character", extra={"type": "artist"})
        elif len(album_name) < 1:
            raise TooShort("album name too short, must be longer than 1 character", extra={"type": "album"})
        elif len(song_name) < 1:
            raise TooShort("artist name too short, must be longer than 1 character", extra={"type": "song"})

        # todo: decide whether i want to make only a set amount of tags available

        if request_id in self.song_information:
            raise  # todo: check which error to raise

        async with self._lock:
            self.song_information[request_id] = {
                "user_id": user_id,
                "tags": tags,
                "artist_name": artist_name,
                "album_name": album_name,
                "song_name": song_name,
                "song_id": song_id,
                "cover_art_id": cover_art_id,
                "image_ids": image_ids
            }

    async def upload_song_finish(
            self,
            db_pool: asqlite.Pool,
            client_package: ClientPackage,
            client_message: ClientMessage,
            user_cache: UserCache
    ):
        """
        this function is used in order to finalize a song's information and data into the database

        this function is tied to song/upload/finish (POST)

        expected payload:
        {
            "request_id": str
        }

        expected output:
        None

        expected cache pre-function:
        > address
        > iv
        > aes_key
        > user_id
        > session_token

        expected cache post-function:
        > address
        > iv
        > aes_key
        > user_id
        > session_token
        """

        client = client_package.client
        address = client_package.address

        # checks if the client has completed the key exchange
        if not client.key or not client.iv:
            raise NoEncryption("missing encryption values: please re-authenticate")

        client_user_cache: UserCacheItem = user_cache[address]
        user_id: str = client_user_cache.user_id

        payload = client_message.payload

        try:
            request_id: str = payload["request_id"]
        except KeyError:
            payload_keys = " ".join(f"\"{key}\"" for key in payload.keys())
            raise InvalidPayload(
                f"Invalid payload passed. expected keys \"request_id\", instead got {payload_keys}")

        if request_id not in self.song_information:
            raise InvalidPayload(f"request ID {request_id} is an invalid ID and does not exist")

        try:
            song_data = self.song_information[request_id]

            # these are not the DB ids, but rather the file-request IDs
            audio_file_id = song_data["song_id"]
            cover_art_file_id = song_data["cover_art_id"]
            sheet_images_file_ids = song_data["image_ids"]

            file_ids = song_data["image_ids"].copy()
            file_ids.append(song_data["cover_art_id"])
            file_ids.append(audio_file_id)

            genres = song_data["tags"]
            artist_name = song_data["artist_name"]
            album_name = song_data["album_name"]
            song_name = song_data["song_name"]

            # due to the async nature of my server, sometimes the client's "song/upload/finish" arrives before the server
            # actually finishes processing the chunks. to deal with it, i implemented a 100 second "timer" that will wait
            # until all the files finish processing

            # ensures that only the "valid" file IDs get added to the set (and not empty ones)
            file_ids_request_set: set[str] = set([set_file_id for set_file_id in file_ids if set_file_id])

            # how long the function is willing to wait before raising an error
            interval_amount = 100
            while not file_ids_request_set.issubset(self.base_file_set.get(request_id, {})):
                interval_amount -= 1
                await asyncio.sleep(1)  # Wait for the interval before checking again

                if interval_amount <= 0:
                    raise Exception(f"upload song finish function timed out for request {request_id}")

            audio_length = await get_audio_length(self.base_file_paths[(request_id, audio_file_id)])

            async with db_pool.acquire() as connection:
                async with connection.transaction():
                    for file_id in file_ids:
                        if not file_id:
                            continue

                        file_request_id_pair = request_id, file_id

                        base_file_information = self.base_file_parameters[file_request_id_pair]

                        await FileSystem.create_base_file(
                            connection=connection,
                            **base_file_information
                        )

                    song_id = await Music.add_song(
                        connection=connection,
                        user_id=user_id,
                        artist_name=artist_name,
                        album_name=album_name,
                        song_name=song_name,
                        song_length_milliseconds=audio_length
                    )

                    audio_base_file_id = self.base_file_parameters[(request_id, audio_file_id)]["file_id"]
                    audio_file_path = self.base_file_paths[(request_id, audio_file_id)]
                    await MediaFiles.create_audio_file(
                        connection=connection,
                        song_id=song_id,
                        file_id=audio_base_file_id,
                        file_path=audio_file_path
                    )

                    del self.base_file_parameters[(request_id, audio_file_id)]
                    del self.base_file_paths[(request_id, audio_file_id)]

                    if cover_art_file_id:
                        cover_art_base_file_id = self.base_file_parameters[(request_id, cover_art_file_id)]["file_id"]
                        cover_art_file_path = self.base_file_paths[(request_id, cover_art_file_id)]
                        await MediaFiles.create_cover_art_file(
                            connection=connection,
                            song_id=song_id,
                            file_id=cover_art_base_file_id,
                            file_path=cover_art_file_path
                        )

                        del self.base_file_parameters[(request_id, cover_art_file_id)]
                        del self.base_file_paths[(request_id, cover_art_file_id)]

                    if sheet_images_file_ids:
                        sheet_music_file_ids: list[str] = []
                        sheet_music_file_paths: list[str] = []
                        for sheet_image_id in sheet_images_file_ids:
                            sheet_base_file_id = self.base_file_parameters[(request_id, sheet_image_id)]["file_id"]
                            sheet_music_file_path = self.base_file_paths[(request_id, sheet_image_id)]

                            sheet_music_file_ids.append(sheet_base_file_id)
                            sheet_music_file_paths.append(sheet_music_file_path)

                            del self.base_file_parameters[(request_id, sheet_image_id)]
                            del self.base_file_paths[(request_id, sheet_image_id)]

                        await MediaFiles.create_sheet_file(
                            connection=connection,
                            song_id=song_id,
                            file_ids=sheet_music_file_ids,
                            file_paths=sheet_music_file_paths
                        )

                    await Music.add_genre(
                        connection=connection,
                        song_id=song_id,
                        genres=genres
                    )

            del self.song_information[request_id]
        except Exception as e:
            print(e)
            traceback.print_exc()
            raise e

    async def upload_song_file(
            self,
            db_pool: asqlite.Pool,
            client_package: ClientPackage,
            client_message: ClientMessage,
            user_cache: UserCache
    ):
        """
        this function is used in order to upload file bytes in chunks. it later uses the information gathered in order
        to build the full file and save it

        this function is tied to song/upload (POST)

        expected payload:
        {
            "request_id": str,
            "file_type": str,
            "file_id": str,
            "chunk": bytes,
            "chunk_number": int,
            "is_last_chunk": bool,
            "expected_size": int
        }

        expected output (after the last chunk):
        {
            "shazam_artist_name": str,
            "shazam_album_name": str,
            "shazam_song_name": str
        }

        expected cache pre-function:
        > address
        > iv
        > aes_key
        > user_id
        > session_token

        expected cache post-function:
        > address
        > iv
        > aes_key
        > user_id
        > session_token
        """

        # we do not initialize the filesystem as the save dir should already be created when running server.py
        file_system = System(db_pool=db_pool)

        client = client_package.client
        address = client_package.address

        # checks if the client has completed the key exchange
        if not client.key or not client.iv:
            raise NoEncryption("missing encryption values: please re-authenticate")

        client_user_cache: UserCacheItem = user_cache[address]
        user_id: str = client_user_cache.user_id

        payload = client_message.payload

        try:
            request_id: str = payload["request_id"]
            # todo: use file_type in order to correctly save the file info into the db
            # "audio" for the song itself
            # "sheet" for the sheet music
            # "cover" for the song thumbnail (which is also "image" but should have it's own table
            # todo: create "thumbnail" table in db
            file_type: str = payload["file_type"]
            file_id: str = payload["file_id"]
            chunk: bytes = payload["chunk"]
            chunk_number: int = payload["chunk_number"]
            is_last_chunk: bool = payload["is_last_chunk"]
            expected_file_size: int = payload["expected_size"]
        except KeyError:
            payload_keys = " ".join(f"\"{key}\"" for key in payload.keys())
            raise InvalidPayload(
                f"Invalid payload passed. expected keys \"request_id\", \"file_type\", \"file_id\", \"chunk\", "
                f"\"chunk_number\", \"is_last_chunk\", \"expected_size\", instead got {payload_keys}")

        # if the request was invalid (or was invalidated due to an internal error), it shouldn't try to upload the
        # files
        if request_id not in self.song_information:
            raise InvalidPayload(f"request ID {request_id} details were not found or are invalid/were invalidated")

        #async with self._lock:
        # checks if the file chunks have already started, or if the current chunk is the first of the file
        chunk_info = self.file_save_ids.get((request_id, file_id), {})

        if not chunk_info:
            print(f"created new file ID for request {request_id}")
            print((request_id, file_id) in self.file_save_ids)
            # creates a new file ID and finds/creates a cluster ID

            async with self._lock:
                save_directory, cluster_id, full_file_id = await file_system.get_id()

                # sets the current request-file ID pair to have the path values. on top of that it sets the current_size
                # to 0 so that it can start growing from later chunks
                self.file_save_ids[(request_id, file_id)] = {
                    "paths": (save_directory, cluster_id, full_file_id),
                    "current_size": 0,
                    "file_extension": None,
                    "previous_chunk": 0,
                    "lock": asyncio.Lock(),
                }

                chunk_info = self.file_save_ids[(request_id, file_id)]
        else:
            # loads the values from the dictionary, so that they can be transferred into the FileChunk in order to be
            # saved onto the disc later on
            save_directory, cluster_id, full_file_id = chunk_info["paths"]

        current_size = chunk_info["current_size"]
        file_extension: str = chunk_info["file_extension"]
        previous_chunk: int = chunk_info["previous_chunk"]
        file_lock: asyncio.Lock = chunk_info["lock"]

        # we define this outside so that we can use it even if the chunks are in order
        new_ordered_chunks = []
        if previous_chunk + 1 != chunk_number:
            async with self._lock:
                # Ensure the out-of-order list exists for the current file
                if (request_id, file_id) not in self.out_of_order_chunks:
                    self.out_of_order_chunks[(request_id, file_id)] = []

                out_of_order_chunks_list = self.out_of_order_chunks[(request_id, file_id)]

                # Insert the out-of-order chunk while maintaining sorted order
                bisect.insort(out_of_order_chunks_list, (chunk_number, chunk))

                # Process chunks in order if possible
                while out_of_order_chunks_list and out_of_order_chunks_list[0][0] == previous_chunk + 1:
                    unordered_number, unordered_chunk = out_of_order_chunks_list.pop(0)
                    new_ordered_chunks.append(unordered_chunk)
                    previous_chunk += 1  # Update to the latest chunk number

                # Update `previous_chunk` in the chunk info dictionary
                self.file_save_ids[(request_id, file_id)]["previous_chunk"] = previous_chunk
        else:
            # see to do at the top of self.compress
            # compressed_chunk = await self.compress(chunk)

            # adds the chunk size (in Bytes) to the total file size
            chunk_size = len(chunk)
            current_size += chunk_size

            #async with self._lock:
            # change the previous chunk to be the current chunk so that we can check it for the next chunk
            chunk_info["previous_chunk"] = previous_chunk + 1

            chunk_info["current_size"] = current_size

        file_chunk = FileChunk(
            asyncio_lock=file_lock,
            chunk=chunk,
            cluster_id=cluster_id,
            file_id=full_file_id,
            save_directory=save_directory,
            chunk_number=chunk_number,
            current_file_size=current_size,
            file_extension=file_extension,
            out_of_order_chunks=new_ordered_chunks
        )

        # checks if the "extension reader" is able to detect the file extension of the chunk
        if file_chunk.file_extension:
            # if it does exist it means:
            # 1) the chunk is a valid chunk (as in, the extension is of a type that the server can accept)
            # 2) the chunk is indeed the first chunk
            async with self._lock:
                chunk_info["file_extension"] = file_chunk.file_extension
        else:
            # if the chunk's extension isn't found it means:
            # 1) either the chunk is not valid
            # 2) it isn't the first chunk

            # we then set the current chunk's extension to whatever we have saved before (if any)
            file_chunk.file_extension = file_extension

        # note that if the chunk goes to be saved and has **no file extension** (None), the whole file may be dismissed as invalid

        # todo: add the above comment as functional code

        try:
            chunk_file_information = await file_system.save_stream(
                chunk=file_chunk,
                uploaded_by_id=user_id,
                is_last_chunk=is_last_chunk,
                chunk_content_type=file_type
            )
        except Exception as e:

            # removes any current data about the chunks
            await self._delete_chunk_info(request_id, file_id)

            # todo: add a system that deletes the previously saved chunks

            logging.error(e, exc_info=True)
            raise e

        if is_last_chunk:
            if current_size != expected_file_size:
                raise Exception(f"received file size was less or more than expected (by {abs(current_size - expected_file_size)} bytes)")
                # todo: add a system to delete the files on error so we don't have necessary files
                # i will also probably invalidate the entire request if any part of it errors, so that users will have
                # to upload the whole request again instead of having missing information in the upload

            print("last chunk was sent. deleting info now")
            # todo: add saving the file to the audio/image table
            await self._delete_chunk_info(request_id, file_id)

            self.base_file_parameters[(request_id, file_id)] = chunk_file_information

            new_file_id = chunk_file_information["file_id"]

            # the save directory already has the cluster ID inside of it, so we don't need to add it
            self.base_file_paths[(request_id, file_id)] = os.path.join(save_directory, new_file_id)

            if request_id in self.base_file_set:
                self.base_file_set[request_id].add(file_id)
            else:
                self.base_file_set[request_id] = {file_id}

    async def _delete_chunk_info(self, request_id: str, file_id: str):
        """tries to delete the information saved about a specific file's chunks"""

        async with self._lock:
            try:
                del self.file_save_ids[(request_id, file_id)]
                del self.out_of_order_chunks[(request_id, file_id)]
            except KeyError:
                pass


async def send_song_previews(
        db_pool: asqlite.Pool,
        client_package: ClientPackage,
        client_message: ClientMessage,
        user_cache: UserCache):
    """
    this function is used to send the client the "preview" of the songs, that contains the cover art, and the standard
    song data (song name, artist name, etc...)

    this function is tied to song/download/preview (POST)

    expected payload:
    {
        "query": str
    }

    -- note: the output will be sent as chunks and multiple "messages". so the output here will be shown as a single
    message for a single song preview.
    --note: this function will only FETCH the song information from the database, the chunk sending will happen in a
    Utils function (outside of server_actions)

    expected output (for starting message):
    {
        "file_id": str
        "song_id": int,
        "artist_name": str,
        "album_name": str,
        "song_name": str,
        "genres": list[str]
    }

    expected output (for each chunk):
    {
        -- note: the chunk's bytes are b64 encoded before sending due to flet limitations
        "chunk": str,
        "file_id": str,
        "chunk_number": int,
        "is_last_chunk": bool,
        "song_id": int
    }

    expected  cache pre - function:
    > address
    > iv
    > aes_key
    > user_id
    > session_token

    expected cache post - function:
    > address
    > iv
    > aes_key
    > user_id
    > session_token
    """

    client = client_package.client
    address = client_package.address

    # checks if the client has completed the key exchange
    if not client.key or not client.iv:
        raise NoEncryption("missing encryption values: please re-authenticate")

    # gets the UserCacheItem for this specific client (and references it)
    client_user_cache: UserCacheItem = user_cache[address]

    payload = client_message.payload

    try:
        search_query = payload["query"]
    except KeyError:
        payload_keys = " ".join(f"\"{key}\"" for key in payload.keys())
        raise InvalidPayload(
            f"Invalid payload passed. expected key \"username\", \"password\", instead got {payload_keys}")

    if len(search_query) > 100:
        raise TooLong("search query is too long, max length allowed is 100 characters", extra={"type": "search"})

    # todo: add the isinstance check for all of the other functions in this file
    if not isinstance(search_query, str):
        raise InvalidDataType(f"expected data type for \"query\" is str, got {type(search_query)} instead", extra={"type": "search"})

    async with db_pool.acquire() as connection:
        matching_song_ids = await MusicSearch.search_song(
            connection=connection,
            search_query=search_query
        )

    await send_song_preview_chunks(transport=client, song_ids=matching_song_ids, db_pool=db_pool)
