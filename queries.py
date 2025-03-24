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
            cluster_id: str | None,
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

        # since you can upload songs without cover images, the default cover image is stored in 1 place and does not
        # need to be added to a cluster. and this the cluster ID *can* be None
        if cluster_id:
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
    ) -> list[str]:
        if not song_ids:
            return []

        # Use a parameterized query to prevent SQL injection
        placeholders = ", ".join(["?"] * len(song_ids))  # Create placeholders (?, ?, ?, ...)
        query = f"""
           SELECT file_path
           FROM media_files
           WHERE song_id IN ({placeholders})
           ORDER BY song_id; -- Ensures the order matches the song_ids list
           """

        results = await connection.fetchall(query, tuple(song_ids))

        # Extract the file_path values from the results
        return [row[0] for row in results]

    @staticmethod
    async def bulk_fetch_preview_paths(
            connection: ProxiedConnection,
            song_ids: list[int],
            default_cover_image_path: str = None
    ) -> list[str]:
        if not song_ids:
            return []

        # Use a parameterized query to prevent SQL injection
        placeholders = ", ".join(["?"] * len(song_ids))  # Create placeholders (?, ?, ?, ...)
        query = f"""
           SELECT song_id, file_path
           FROM media_files
           WHERE song_id IN ({placeholders}) AND file_type = 'cover'
           """

        results = await connection.fetchall(query, tuple(song_ids))

        # Create a mapping of song_id to file_path
        song_paths = {row[0]: row[1] for row in results}

        # Ensure all song_ids are accounted for, using a default path if missing
        return [song_paths.get(song_id, default_cover_image_path) for song_id in song_ids]


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

        # Insert the song name into the spellfix1 table
        await connection.execute(
            """
            INSERT INTO song_name_trigrams (word)
            VALUES (?);
            """, (song_name,)
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
           """

        results = await connection.fetchall(query, tuple(song_ids))

        # Create a dictionary mapping song_id to its corresponding result
        result_dict = {
            row[0]: {
                "song_id": row[0],
                "artist_name": row[1],
                "album_name": row[2],
                "song_name": row[3],
                "song_length": row[4],
                "genres": row[5].split(",") if row[5] else []  # Split the comma-separated string into a list
            }
            for row in results
        }

        # Return results in the same order as the input song_ids
        return [result_dict.get(song_id, {}) for song_id in song_ids]

    @staticmethod
    async def bulk_fetch_song_preview_data(
            connection: ProxiedConnection,
            song_ids: list[int],
            default_cover_image_path: str = None,
    ) -> list[tuple[str, dict[str, str | int]]]:
        async with connection.transaction():
            song_paths = await MediaFiles.bulk_fetch_preview_paths(connection=connection, song_ids=song_ids, default_cover_image_path=default_cover_image_path)
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
    async def search_song(connection, search_query: str, limit: int = 10):
        """returns a list of song IDs based off of a search query if given, else returns a random list of song IDs"""
        if search_query:
            return await MusicSearch.search_song_by_name(connection=connection, search_query=search_query, limit=limit)

        return await MusicSearch.get_random_songs(connection=connection, limit=limit)

    @staticmethod
    async def search_song_by_name(connection, search_query: str, limit: int = 10, fuzzy_precession: int = 5) -> list[int]:
        """
        Searches for songs by name using FTS5 and spellfix, and returns the top 'limit' results ordered by relevance.

        :param connection: Database connection object.
        :param search_query: Search string entered by the user.
        :param limit: Number of results to return.
        :param fuzzy_precession: how exact the fuzzy search (using spellfix1) is. the larger the number, the broader it is
        (default 5)
        :return: List of song IDs ordered by relevance.
        """
        # Prepare the search terms
        search_query_fts5 = f"{search_query}*"  # For prefix matching in FTS5
        search_query_like = f"{search_query}%"  # For prefix matching in spellfix1

        # Execute the FTS5 query with ordering
        fts5_results = await connection.fetchall(
            """
            SELECT song_info.song_id, bm25(song_info_fts) AS relevance
            FROM song_info_fts
            JOIN song_info ON song_info_fts.rowid = song_info.song_id
            WHERE song_info_fts.song_name MATCH ?
            ORDER BY relevance ASC
            LIMIT ?;
            """, (search_query_fts5, limit)
        )

        # Execute the spellfix query with ordering
        spellfix_results = await connection.fetchall(
            """
            SELECT song_info.song_id, editdist3(song_name_trigrams.word, ?) AS relevance
            FROM song_info
            JOIN song_name_trigrams ON song_name_trigrams.rowid = song_info.song_id
            WHERE song_name_trigrams.word LIKE ?
              AND editdist3(song_name_trigrams.word, ?) <= ?
            ORDER BY relevance ASC
            LIMIT ?;
            """, (search_query, search_query_like, search_query, fuzzy_precession, limit)
        )

        # Combine results, sorting by relevance
        combined_results = fts5_results + spellfix_results
        sorted_results = sorted(combined_results, key=lambda x: x[1])  # Sort by relevance (lower is better)

        # Extract the song IDs, ensuring no duplicates
        matching_song_ids = list({row[0] for row in sorted_results})[:limit]

        return matching_song_ids

    @staticmethod
    async def get_random_songs(connection, limit: int = 10) -> list[int]:
        """
        Fetches random songs from the song_info table based on a given limit.

        :param connection: Database connection object.
        :param limit: The number of random songs to retrieve.
        :return: List of random song IDs.
        """
        # Execute the query to fetch random song IDs
        random_songs = await connection.fetchall(
            """
            SELECT song_id
            FROM song_info
            ORDER BY RANDOM()
            LIMIT ?;
            """, (limit,)
        )

        # Return the list of random song IDs
        return [row[0] for row in random_songs]


