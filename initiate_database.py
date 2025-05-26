import sqlite3
import os

spell_fix_extension = os.path.abspath("./Sqlite3Extensions/spellfix.dll")


class CreateTables:
    def __init__(self, database: str):
        self.database = database

    def init(self):
        connection = None
        try:
            connection = sqlite3.connect(self.database)
            connection.enable_load_extension(True)

            cursor = connection.cursor()

            # Load extensions
            self._load_extensions(cursor)

            # Create tables
            self._create_users(cursor)
            self._create_file_cluster_table(cursor)
            self._create_file_table(cursor)
            self._create_song_info_table(cursor)
            self._create_media_files_table(cursor)
            self._create_genres_table(cursor)
            self._create_favorite_genres_tale(cursor)
            self._create_comments_table(cursor)
            self._create_ai_summarization_comments_table(cursor)
            self._create_favorite_songs_table(cursor)

            # Commit changes
            connection.commit()
        except Exception as e:
            raise e
        finally:
            if connection:
                connection.close()

    def _load_extensions(self, cursor):
        try:
            cursor.execute(f"SELECT load_extension('{spell_fix_extension}');")
            print("Extension loaded successfully!")
        except sqlite3.OperationalError as e:
            print(f"Error loading extension: {e}")
            raise

    @staticmethod
    def _create_users(cursor):
        cursor.execute(
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
    def _create_file_cluster_table(cursor):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS clusters (
                cluster_id TEXT PRIMARY KEY,
                current_size INTEGER NOT NULL DEFAULT 0
            );
            """
        )

    @staticmethod
    def _create_file_table(cursor):
        cursor.execute(
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

    def _create_song_info_table(self, cursor):
        # Create the main table for song information
        cursor.execute(
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

        # Create an FTS5 virtual table for song_name
        cursor.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS song_info_fts
            USING fts5(song_name, content='song_info', content_rowid='song_id', prefix='2 3 4');
            """
        )

        # Create the spellfix1 virtual table for trigram-based fuzzy matching
        cursor.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS song_name_trigrams
            USING spellfix1;
            """
        )

    @staticmethod
    def _create_genres_table(cursor):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS genres (
                song_id INTEGER NOT NULL,
                genre_name TEXT NOT NULL,
                PRIMARY KEY (song_id, genre_name),
                FOREIGN KEY (song_id) REFERENCES song_info (song_id) ON DELETE CASCADE
            );
            """
        )

    @staticmethod
    def _create_media_files_table(cursor):
        """This is instead of "audio_file", "sheet_file" and "cover_art_file" tables."""
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS media_files (
                song_id INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                file_type TEXT NOT NULL, -- e.g., 'audio', 'sheet', 'cover'
                file_path TEXT NOT NULL, -- the full file path (save_dir/cluster/file)
                PRIMARY KEY (song_id, file_id),
                FOREIGN KEY (song_id) REFERENCES song_info (song_id) ON DELETE CASCADE,
                FOREIGN KEY (file_id) REFERENCES files (file_id) ON DELETE CASCADE
            );
            """
        )

    @staticmethod
    def _create_favorite_genres_tale(cursor):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS favorite_genres (
                user_id TEXT NOT NULL,
                genre TEXT NOT NULL,
                score INTEGER NOT NULL,
                PRIMARY KEY (user_id, genre)
            );
            """
        )

    @staticmethod
    def _create_comments_table(cursor):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS song_comments (
                comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                comment_text TEXT NOT NULL,
                song_id INTEGER NOT NULL,
                uploaded_by TEXT NOT NULL,
                uploaded_at INTEGER NOT NULL,
                FOREIGN KEY (song_id) REFERENCES song_info (song_id) ON DELETE CASCADE,
                FOREIGN KEY (uploaded_by) REFERENCES users (user_id)
            );
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_song_comments_song_id ON song_comments(song_id);
            """
        )

    @staticmethod
    def _create_ai_summarization_comments_table(cursor):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_comment_summary (
                song_id INTEGER PRIMARY KEY,
                summary TEXT NOT NULL,
                last_updated INTEGER NOT NULL,
                FOREIGN KEY (song_id) REFERENCES song_info (song_id) ON DELETE CASCADE
            );
            """
        )

    @staticmethod
    def _create_favorite_songs_table(cursor):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS favorite_songs (
                song_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                PRIMARY KEY (song_id, user_id),
                FOREIGN KEY (song_id) REFERENCES song_info (song_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            );
            """
        )


if __name__ == "__main__":
    # Define the database path
    database_name = "database.db"

    # Initialize the database and create tables
    try:
        tables = CreateTables(database_name)
        tables.init()
    except Exception as e:
        print(f"An error occurred: {e}")
