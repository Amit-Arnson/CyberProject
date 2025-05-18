# this file is used as a way to organize all the needed SQL queries
import time

from asqlite import ProxiedConnection
from sqlite3 import Row

from Utils.chunk import FileTypes

from GroqAI.generate_comment_summary import summarize
from GroqAI.api import hybrid_token_estimate


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
    async def fetch_preview_path(
            connection: ProxiedConnection,
            song_id: int,
            default_cover_image_path: str = None
    ) -> str:
        query = f"""
           SELECT file_path
           FROM media_files
           WHERE song_id = ? AND file_type = 'cover'
        """

        result = await connection.fetchone(query, song_id)

        if not result:
            return default_cover_image_path

        return result[0]

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

    @staticmethod
    async def fetch_audio_path(
            connection: ProxiedConnection,
            song_id: int,
    ) -> str | None:
        query = f"""
           SELECT file_path
           FROM media_files
           WHERE song_id = ? AND file_type = 'audio'
        """

        result = await connection.fetchone(query, song_id)

        if not result:
            return None

        return result[0]

    @staticmethod
    async def fetch_sheet_image_paths(
            connection: ProxiedConnection,
            song_id: int,
    ) -> list[str]:
        query = f"""
           SELECT file_path
           FROM media_files
           WHERE song_id = ? AND file_type = 'sheet'
        """

        results = await connection.fetchall(query, song_id)

        if not results:
            return []

        return [result[0] for result in results]


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
    async def search_song(connection: ProxiedConnection, search_query: str, exclude: list[int], limit: int = 10):
        """returns a list of song IDs based off of a search query if given, else returns a random list of song IDs"""
        if search_query:
            return await MusicSearch.search_song_by_name(
                connection=connection,
                search_query=search_query,
                limit=limit,
                exclude=exclude
            )

        return await MusicSearch.get_random_songs(connection=connection, limit=limit, exclude=exclude)

    @staticmethod
    async def search_song_by_name(connection: ProxiedConnection,
                                  search_query: str,
                                  exclude: list[int],
                                  limit: int = 10,
                                  fuzzy_precession: int = 5) -> list[int]:
        """
        Searches for songs by name using FTS5 and spellfix, and returns the top 'limit' results ordered by relevance.

        :param connection: Database connection object.
        :param search_query: Search string entered by the user.
        :param exclude: the list of song IDs to not include in the search
        :param limit: Number of results to return.
        :param fuzzy_precession: how exact the fuzzy search (using spellfix1) is. the larger the number, the broader it is
        (default 5)
        :return: List of song IDs ordered by relevance.
        """
        # Prepare the search terms
        search_query_fts5 = f'"{search_query}*"'  # For prefix matching in FTS5
        search_query_like = f'"{search_query}%"'  # For prefix matching in spellfix1

        exclude_placeholders = ", ".join(["?"] * len(exclude)) if exclude else "NULL"  # Prevent empty placeholders
        exclude_clause = f"AND song_info.song_id NOT IN ({exclude_placeholders})" if exclude else ""

        fts5_params = (search_query_fts5, *exclude, limit) if exclude else (search_query_fts5, limit)

        # Execute the FTS5 query with ordering
        fts5_results = await connection.fetchall(
            f"""
            -- 'bm25(song_info_fts)' calculates relevance based on the BM25 algorithm, which ranks text matches by relevance.
            SELECT song_info.song_id, bm25(song_info_fts) AS relevance
            FROM song_info_fts

            JOIN song_info ON song_info_fts.rowid = song_info.song_id -- Connects the FTS5 row IDs to actual song IDs
            -- 'song_info_fts' is the full-text search table created using FTS5. Its row IDs map to the corresponding song entries in 'song_info'.
            
            -- Matches song names using FTS5's full-text search (e.g., "duc*" matches "duck")
            WHERE song_info_fts.song_name MATCH ? {exclude_clause}              

            ORDER BY relevance ASC

            LIMIT ?;
            """, fts5_params
        )

        spellfix_params = (search_query, search_query_like, search_query, fuzzy_precession, *exclude, limit)\
            if exclude else (search_query, search_query_like, search_query, fuzzy_precession, limit)

        # Execute the spellfix query with ordering
        spellfix_results = await connection.fetchall(
            f"""
            SELECT song_info.song_id, editdist3(song_name_trigrams.word, ?) AS relevance
            FROM song_info

            JOIN song_name_trigrams ON song_name_trigrams.rowid = song_info.song_id -- Connects trigram row IDs to actual song IDs
            -- 'song_name_trigrams' stores word fragments (trigrams) for fuzzy search. Each row represents a word, broken into trigrams (e.g., "world" -> "wor", "orl", "rld").

            WHERE song_name_trigrams.word LIKE ? -- Performs a prefix match for similar words (e.g., "worl%" matches "world")                
              AND editdist3(song_name_trigrams.word, ?) <= ? -- Filters words within the given edit distance threshold (using fuzzy search)
              {exclude_clause} 
            
            
            ORDER BY relevance ASC
            LIMIT ?;
            """, spellfix_params
        )

        # Combine results, sorting by relevance
        combined_results = fts5_results + spellfix_results
        sorted_results = sorted(combined_results, key=lambda x: x[1])  # Sort by relevance (lower is better)

        # Extract the song IDs, ensuring no duplicates
        matching_song_ids = list({row[0] for row in sorted_results})[:limit]

        return matching_song_ids

    @staticmethod
    async def search_song_by_genres(connection: ProxiedConnection, genres: list[str], exclude: list[int], limit: int = 10) -> list[int]:
        if not genres:
            return []

        placeholders = ", ".join(["?"] * len(genres))  # Create placeholders (?, ?, ?, ...)

        exclude_placeholders = ", ".join(["?"] * len(exclude))
        exclude_query = f"AND song_id NOT IN ({exclude_placeholders})" if exclude else ""

        results = await connection.fetchall(
            f"SELECT song_id FROM genres WHERE genre_name IN ({placeholders}) {exclude_query} LIMIT ?;",
            *genres, *exclude, limit
        )

        return [row[0] for row in results]

    @staticmethod
    async def search_song_by_inclusion(connection: ProxiedConnection, include: list[int], exclude: list[int], limit: int = 10) -> list[int]:
        if not include:
            return []

        exclude_placeholders = ", ".join(["?"] * len(exclude))
        exclude_query = f"AND song_id NOT IN ({exclude_placeholders})" if exclude else ""

        include_placeholders = ", ".join(["?"] * len(include))

        results = await connection.fetchall(
            f"SELECT song_id FROM song_info WHERE song_id  IN ({include_placeholders}) {exclude_query} LIMIT ?;",
            *include, *exclude, limit
        )

        return [row[0] for row in results]

    @staticmethod
    async def search_song_by_artist(connection: ProxiedConnection, artists: list[str], exclude: list[int], limit: int = 10) -> list[int]:
        if not artists:
            return []

        placeholders = ", ".join(["?"] * len(artists))  # Create placeholders (?, ?, ?, ...)

        exclude_placeholders = ", ".join(["?"] * len(exclude))
        exclude_query = f"AND song_id NOT IN ({exclude_placeholders})" if exclude else ""

        results = await connection.fetchall(
            f"SELECT song_id FROM song_info WHERE artist_name IN ({placeholders}) {exclude_query} LIMIT ?;",
            *artists, limit
        )

        return [row[0] for row in results]

    @staticmethod
    async def search_song_by_length(connection: ProxiedConnection, exclude: list[int], maximum: int | None = None, minimum: int = 0, limit: int = 10) -> list[int]:
        search_parameters = [minimum]

        upper_limit_query = ""
        if maximum:
            upper_limit_query = " AND song_length < ?"
            search_parameters.append(maximum)

        exclude_placeholders = ", ".join(["?"] * len(exclude))
        exclude_query = f"AND song_id NOT IN ({exclude_placeholders})" if exclude else ""

        results = await connection.fetchall(
            f"""SELECT song_id FROM song_info WHERE song_length > ? {upper_limit_query} {exclude_query} LIMIT ?;""",
            *search_parameters, limit
        )

        return [row[0] for row in results]

    @staticmethod
    async def get_random_songs(connection: ProxiedConnection, exclude: list[int], limit: int = 10) -> list[int]:
        """
        Fetches random songs from the song_info table based on a given limit.

        :param connection: Database connection object.
        :param exclude: the list of song IDs to specifically exclude from the search
        :param limit: The number of random songs to retrieve.
        :return: List of random song IDs.
        """

        exclude_placeholders = ", ".join(["?"] * len(exclude))
        exclude_query = f"WHERE song_id NOT IN ({exclude_placeholders})" if exclude else ""

        # Execute the query to fetch random song IDs
        random_songs = await connection.fetchall(
            f"""
            SELECT song_id
            FROM song_info {exclude_query} 
            ORDER BY RANDOM()
            LIMIT ?;
            """, *exclude, limit
        )

        # Return the list of random song IDs
        return [row[0] for row in random_songs]

    @staticmethod
    async def get_genre_names(connection: ProxiedConnection, exclude: list[str]) -> list[str]:
        exclude_placeholders = ", ".join(["?"] * len(exclude))
        exclude_query = f"WHERE genre_name NOT IN ({exclude_placeholders})" if exclude else ""

        genres = await connection.fetchall(
            f"""
             SELECT genre_name
             FROM genres {exclude_query} 
             LIMIT 100
             """, *exclude
        )

        return list(set([genre[0] for genre in genres]))


class RecommendationAlgorithm:
    @staticmethod
    async def increase_genre_score_by_song_id(connection: ProxiedConnection, user_id: str, song_id: int, score_increase: int):
        genres: list[Row] = await connection.fetchall(
            """SELECT genre_name FROM genres WHERE song_id = ?""",
            song_id,
        )

        values = [(user_id, genre[0], score_increase) for genre in genres]

        await connection.executemany(
            """
            INSERT INTO favorite_genres (user_id, genre, score)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, genre) DO UPDATE SET score = score + excluded.score
            """,
            values
        )

    @staticmethod
    async def increase_genre_score(connection: ProxiedConnection, user_id: str, genre: str, score_increase: int):
        await connection.execute(
            """
            INSERT INTO favorite_genres (user_id, genre, score)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, genre) DO UPDATE SET score = score + excluded.score
            """,
            user_id, genre, score_increase
        )

    @staticmethod
    async def fetch_top_genres(connection: ProxiedConnection, user_id: str) -> list[str]:
        genres = await connection.fetchall(
            """SELECT genre FROM favorite_genres WHERE user_id = ? ORDER BY score DESC""",
            user_id,
        )

        top_10_list: list[str] = [genre[0] for genre in genres][:10]

        return top_10_list

    @staticmethod
    async def fetch_recommended_songs(connection: ProxiedConnection, user_id: str, exclude: list[int], limit: int = 10) -> list[int]:
        recommended_genres = await RecommendationAlgorithm.fetch_top_genres(connection, user_id)

        if not recommended_genres:
            return []

        placeholders = ",".join("?" for _ in recommended_genres)

        exclude_placeholders = ", ".join(["?"] * len(exclude))
        exclude_query = f"AND song_id NOT IN ({exclude_placeholders})" if exclude else ""

        query = f"""
            SELECT song_id FROM genres
            WHERE genre_name IN ({placeholders}) {exclude_query}
            LIMIT ?;
        """

        song_ids = await connection.fetchall(query, *recommended_genres, *exclude, limit)

        return list(set([song_id[0] for song_id in song_ids]))


class Comments:
    @staticmethod
    async def upload_comment(connection: ProxiedConnection, text: str, uploaded_by: str, song_id: int):
        current_time = int(time.time())

        await connection.execute(
            """INSERT INTO song_comments (comment_text, song_id, uploaded_by, uploaded_at) VALUES (?, ?, ?, ?)""",
            text, song_id, uploaded_by, current_time
        )

    @staticmethod
    async def fetch_song_comments(connection: ProxiedConnection, song_id: int, exclude: list[int], limit: int = 100):
        exclude_placeholders = ", ".join(["?"] * len(exclude))
        exclude_query = f"AND song_comments.comment_id NOT IN ({exclude_placeholders})" if exclude else ""

        query = f"""
            SELECT song_comments.*, users.username
            FROM song_comments
            JOIN users ON song_comments.uploaded_by = users.user_id
            WHERE song_comments.song_id = ?
            {exclude_query}
            ORDER BY song_comments.uploaded_at ASC
            LIMIT ?
        """

        comments = await connection.fetchall(query, song_id, *exclude, limit)

        comments_dict = [
            {
                "comment_id": comment[0],
                "text": comment[1],
                "uploaded_at": comment[4],
                "uploaded_by": comment[-1]
            } for comment in comments
        ]

        return comments_dict

    @staticmethod
    async def fetch_ai_summary(connection: ProxiedConnection, song_id: int) -> str:
        current_time = int(time.time())

        try:
            summary = await connection.fetchone(
                """
                SELECT summary, last_updated FROM ai_comment_summary WHERE song_id = ?
                """,
                song_id
            )

            one_hour = 3600
            if not summary or (summary and summary["last_updated"] + one_hour < current_time):
                comments = await connection.fetchall(
                    """
                    SELECT comment_text, comment_id, uploaded_at, uploaded_by
                    FROM song_comments
                    WHERE song_id = ?
                    ORDER BY uploaded_at ASC
                    LIMIT 50
                    """,
                    song_id
                )

                total_token_approximation = 0
                allowed_token_approximation = 1000

                comments_for_summary: list[str] = []

                for comment in comments:
                    comment_text: str = comment[0]

                    # we dont care for whitespace comments
                    if not comment_text:
                        continue

                    # in order to prevent spam comments (like, gibberish), we add an approximation feature to detect
                    # common spam structures (few words with a lot of total length)
                    if len(comment_text.split()) <= 3 and len(comment_text) > 25:
                        continue

                    # on average, sentences will have an average of 5 letters per word, so we add a bit of leeway. but this
                    # with combination of the first statement should be a good way to remove most spam comments
                    if len(comment_text) / len(comment_text.split()) > 9:
                        continue

                    total_token_approximation += hybrid_token_estimate(comment_text)

                    if total_token_approximation >= allowed_token_approximation:
                        break

                    comments_for_summary.append(comment_text)

                if not comments_for_summary:
                    return "Not enough comments for AI summary"

                song_name = await connection.fetchone(
                    """SELECT song_name FROM song_info WHERE song_id = ?""",
                    song_id
                )

                song_name = song_name[0]

                comment_summary = await summarize(comments_for_summary, song_name=song_name)

                await connection.execute(
                    """
                    INSERT INTO ai_comment_summary (song_id, summary, last_updated)
                    VALUES (?, ?, ?)
                    ON CONFLICT(song_id) DO UPDATE SET
                        summary = excluded.summary,
                        last_updated = excluded.last_updated
                    """,
                    song_id, comment_summary, current_time
                )

                return comment_summary
            else:
                return summary[0]
        except Exception as e:
            print(e)
