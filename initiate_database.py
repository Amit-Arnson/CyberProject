import asqlite
import asyncio

from asqlite import Cursor


class CreateTables:
    def __init__(self, database: str):
        self.database = database

    async def aio_init(self):

        # this code will only be run once at the start of runtime. for this reason i do not use a DB pool here.
        async with asqlite.connect(self.database) as connection:
            async with connection.cursor() as cursor:
                await self._create_users(cursor)
                await self._create_file_cluster_table(cursor)
                await self._create_file_table(cursor)
                await self._create_song_info_table(cursor)
                await self._create_media_files_table(cursor)
                await self._create_genres_table(cursor)
                # ...

                await connection.commit()

    # all of these methods will create tables
    @staticmethod
    async def _create_users(cursor: Cursor):
        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                display_name TEXT NOT NULL,
                password TEXT NOT NULL,
                salt BLOB NOT NULL
            );
            """
        )

    @staticmethod
    async def _create_file_cluster_table(cursor: Cursor):
        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS clusters (
                cluster_id TEXT PRIMARY KEY,
                current_size INT NOT NULL DEFAULT 0
            );
            """
        )

    # this is for default files. sound and images will have different tables that rely on file_id to identify
    @staticmethod
    async def _create_file_table(cursor: Cursor):
        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                file_id TEXT PRIMARY KEY,
                file_cluster_id TEXT NOT NULL,
                user_uploaded_id TEXT NOT NULL,
                size INTEGER NOT NULL,
                uploaded_at INTEGER,
                raw_file_id TEXT, -- as in, the file ID without the format attached to it
                file_format TEXT
            );
            """
        )

    @staticmethod
    async def _create_song_info_table(cursor: Cursor):
        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS song_info (
                song_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                artist_name TEXT NOT NULL,
                album_name TEXT NOT NULL,
                song_name TEXT NOT NULL,   
                song_length INTEGER NOT NULL
            );
            """
        )

    @staticmethod
    async def _create_genres_table(cursor: Cursor):
        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS genres (
                song_id INTEGER NOT NULL,
                genre_name TEXT NOT NULL,
                PRIMARY KEY (song_id, genre_name),
                FOREIGN KEY (song_id) REFERENCES song_info (song_id)
            );
            """
        )

    @staticmethod
    async def _create_media_files_table(cursor: Cursor):
        """this is instead of "audio_file", "sheet_file" and "cover_art_file" tables"""
        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS media_files (
                song_id INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                file_type TEXT NOT NULL, -- e.g., 'audio', 'sheet', 'cover'
                PRIMARY KEY (song_id, file_id),
                FOREIGN KEY (song_id) REFERENCES song_info (song_id),
                FOREIGN KEY (file_id) REFERENCES files (file_id)
            );
            """
        )


if __name__ == "__main__":
    tables = CreateTables(f"database.db")
    asyncio.run(tables.aio_init())
