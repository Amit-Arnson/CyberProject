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
            file_path: str,
    ):
        await connection.execute(
            """
            INSERT INTO media_files
            (song_id, file_id, file_type, file_path) VALUES (?, ?, ?, ?)
            """,
            song_id, file_id, file_type, file_path
        )

    @staticmethod
    async def bulk_create_media_file(
            connection: ProxiedConnection,
            song_id: int,
            file_ids: list[str],
            file_type: str,
            file_paths: list[str]
    ):
        await connection.executemany(
            """
            INSERT INTO media_files
            (song_id, file_id, file_type, file_path) VALUES (?, ?, ?, ?)
            """,
            [(song_id, file_id, file_type, file_path) for file_id, file_path in zip(file_ids, file_paths)]
        )

    @staticmethod
    async def create_audio_file(
            connection: ProxiedConnection,
            song_id: int,
            file_id: str,
            file_path: str
    ):
        file_type = FileTypes.AUDIO.value

        await MediaFiles.create_media_file(
            connection=connection,
            song_id=song_id,
            file_id=file_id,
            file_type=file_type,
            file_path=file_path
        )

    @staticmethod
    async def create_sheet_file(
            connection: ProxiedConnection,
            song_id: int,
            file_ids: list[str],
            file_paths: list[str],
    ):
        file_type = FileTypes.SHEET.value

        await MediaFiles.bulk_create_media_file(
            connection=connection,
            song_id=song_id,
            file_ids=file_ids,
            file_type=file_type,
            file_paths=file_paths
        )

    @staticmethod
    async def create_cover_art_file(
            connection: ProxiedConnection,
            song_id: int,
            file_id: str,
            file_path: str,
    ):
        file_type = FileTypes.COVER.value

        await MediaFiles.create_media_file(
            connection=connection,
            song_id=song_id,
            file_id=file_id,
            file_type=file_type,
            file_path=file_path,
        )

    @staticmethod
    async def bulk_fetch_paths(
            connection: ProxiedConnection,
            song_ids: list[int],
            preview: bool = True
    ) -> list[str]:
        if not song_ids:
            return []

        preview_mode = "AND file_type = 'cover'" if preview else ""

        # Use a parameterized query to prevent SQL injection
        placeholders = ", ".join(["?"] * len(song_ids))  # Create placeholders (?, ?, ?, ...)
        query = f"""
           SELECT file_path
           FROM media_files
           WHERE song_id IN ({placeholders}) {preview_mode}
           ORDER BY song_id; -- Ensures the order matches the song_ids list
           """

        results = await connection.fetchall(query, tuple(song_ids))

        # Extract the file_path values from the results
        return [row[0] for row in results]


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

        song_id = cursor.get_cursor().lastrowid

        # Index the song_name in the FTS5 table
        await connection.execute(
            """
            INSERT INTO song_info_fts (rowid, song_name)
            VALUES (?, ?);
            """, song_id, song_name
        )

        return song_id

    @staticmethod
    async def bulk_fetch_song_data(
            connection: ProxiedConnection,
            song_ids: list[int],
    ) -> list[dict[str, str | int | list[str]]]:
        if not song_ids:
            return []

        # Use a parameterized query to prevent SQL injection
        placeholders = ", ".join(["?"] * len(song_ids))  # Create placeholders (?, ?, ?, ...)
        query = f"""
           SELECT 
               song_info.song_id,
               artist_name,
               album_name,
               song_name,
               song_length,
               GROUP_CONCAT(genres.genre_name, ',') AS genre_list
           FROM song_info
           LEFT JOIN genres ON song_info.song_id = genres.song_id
           WHERE song_info.song_id IN ({placeholders})
           GROUP BY song_info.song_id
           ORDER BY song_info.song_id; -- Ensure results are ordered
           """

        results = await connection.fetchall(query, tuple(song_ids))

        # Extract the dictionary values from the results
        return [
            {
                "song_id": row[0],
                "artist_name": row[1],
                "album_name": row[2],
                "song_name": row[3],
                "song_length": row[4],
                "genres": row[5].split(",") if row[5] else []  # Split the comma-separated string into a list
            }
            for row in results
        ]

    @staticmethod
    async def bulk_fetch_song_preview_data(
            connection: ProxiedConnection,
            song_ids: list[int]
    ) -> list[tuple[str, dict[str, str | int]]]:
        async with connection.transaction():
            song_paths = await MediaFiles.bulk_fetch_paths(connection=connection, song_ids=song_ids)
            song_data_dicts = await Music.bulk_fetch_song_data(connection=connection, song_ids=song_ids)

        return zip(song_paths, song_data_dicts)

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


class MusicSearch:
    @staticmethod
    async def search_song_by_name(connection: ProxiedConnection, search_query: str) -> list[int]:
        """:returns: a list of the song IDs that closely match the search query"""
        matching_song_id = await connection.fetchall(
            """
            SELECT rowid 
            FROM song_info_fts 
            WHERE song_name MATCH ?;
            """, (search_query,)
        )

        # Extract the song_id values from the tuples
        return [row[0] for row in matching_song_id]
