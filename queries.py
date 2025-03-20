# this file is used as a way to organize all the needed SQL queries
import json
import time

from asqlite import ProxiedConnection
from sqlite3 import Row

from Utils.chunk import FileTypes


class User:
    @staticmethod
    async def create_user(connection: ProxiedConnection, user_id: str, username: str, display_name: str, password: str,
                          salt: bytes) -> None:
        await connection.execute(
            "INSERT INTO users (user_id, username, display_name, password, salt) VALUES (?, ?, ?, ?, ?)",
            user_id, username, display_name, password, salt
        )

    @staticmethod
    async def fetch_user(connection: ProxiedConnection, username: str) -> Row:
        row = await connection.fetchone("SELECT * FROM users WHERE username = ?", username)
        return row

    @staticmethod
    async def user_exists(connection: ProxiedConnection, username: str) -> bool:
        user = await User.fetch_user(connection=connection, username=username)

        if user:
            return True

        return False


class FileSystem:
    # clusters
    @staticmethod
    async def find_free_cluster(connection: ProxiedConnection, max_size: int) -> str | None:
        """:returns: the cluster's name (ID). find files with main_dir/cluster_id/file_id"""

        row = await connection.fetchone("SELECT cluster_id FROM clusters WHERE current_size < ?", max_size)

        if row:
            return row["cluster_id"]

        return None

    @staticmethod
    async def does_cluster_exist(connection: ProxiedConnection, cluster_id: str) -> bool:
        """:returns: whether the cluster exists or not (True means it exists)"""

        cluster = await connection.fetchone("SELECT * FROM clusters WHERE cluster_id = ?", cluster_id)

        if cluster:
            return True

        return False

    @staticmethod
    async def create_new_cluster(connection: ProxiedConnection, cluster_id: str) -> None:
        # default for current_size is 0, so we don't need to set it.
        await connection.execute("INSERT INTO clusters (cluster_id) VALUES (?)", cluster_id)

    # files

    @staticmethod
    async def create_base_file(
            connection: ProxiedConnection,
            cluster_id: str,
            file_id: str,
            raw_file_id: str,
            file_format: str,
            user_uploaded_id: str,
            size: int,
    ) -> None:

        current_time = int(time.time())

        # todo: check what i can do about the "no transaction in transaction" rule
        await connection.execute(
            """
            INSERT INTO files
            (file_id, file_cluster_id, user_uploaded_id, size, uploaded_at, raw_file_id, file_format) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            file_id, cluster_id, user_uploaded_id, size, current_time, raw_file_id, file_format
        )

        await connection.execute(
            """UPDATE clusters SET current_size = current_size + 1 WHERE cluster_id = ?""",
            cluster_id
        )

    @staticmethod
    async def does_file_exist(connection: ProxiedConnection, file_id: str) -> bool:
        """:returns: whether the file exists or not (True means it exists)"""

        file = await connection.fetchone("SELECT * FROM files WHERE file_id = ?", file_id)

        if file:
            return True

        return False


class MediaFiles:
    @staticmethod
    async def create_media_file(
            connection: ProxiedConnection,
            song_id: int,
            file_id: str,
            file_type: str,
    ):
        await connection.execute(
            """
            INSERT INTO media_files
            (song_id, file_id, file_type) VALUES (?, ?, ?)
            """,
            song_id, file_id, file_type
        )

    @staticmethod
    async def bulk_create_media_file(
            connection: ProxiedConnection,
            song_id: int,
            file_ids: list[str],
            file_type: str,
    ):
        await connection.executemany(
            """
            INSERT INTO media_files
            (song_id, file_id, file_type) VALUES (?, ?, ?)
            """,
            [(song_id, file_id, file_type) for file_id in file_ids]
        )

    @staticmethod
    async def create_audio_file(
            connection: ProxiedConnection,
            song_id: int,
            file_id: str,
    ):
        file_type = FileTypes.AUDIO.value

        await MediaFiles.create_media_file(
            connection=connection,
            song_id=song_id,
            file_id=file_id,
            file_type=file_type
        )

    @staticmethod
    async def create_sheet_file(
            connection: ProxiedConnection,
            song_id: int,
            file_ids: list[str],
    ):
        file_type = FileTypes.SHEET.value

        await MediaFiles.bulk_create_media_file(
            connection=connection,
            song_id=song_id,
            file_ids=file_ids,
            file_type=file_type
        )

    @staticmethod
    async def create_cover_art_file(
            connection: ProxiedConnection,
            song_id: int,
            file_id: str,
    ):
        file_type = FileTypes.COVER.value

        await MediaFiles.create_media_file(
            connection=connection,
            song_id=song_id,
            file_id=file_id,
            file_type=file_type
        )


class Music:
    @staticmethod
    async def add_song(
            connection: ProxiedConnection,
            user_id: str,
            artist_name: str,
            album_name: str,
            song_name: str,
            song_length_milliseconds: int
    ):
        """:returns: the song_id of the newly created song entry"""

        cursor = await connection.execute(
            """
            INSERT INTO song_info (user_id, artist_name, album_name, song_name, song_length)
            VALUES (?, ?, ?, ?, ?)
            """, user_id, artist_name, album_name, song_name, song_length_milliseconds
        )

        return cursor.get_cursor().lastrowid

    @staticmethod
    async def add_genre(
            connection: ProxiedConnection,
            song_id: int,
            genres: list[str]
    ):
        await connection.executemany(
            """INSERT INTO genres (song_id, genre_name) VALUES (?, ?)""",
            [(song_id, genre_name) for genre_name in genres]
        )
