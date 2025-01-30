# this file is used as a way to organize all the needed SQL queries
import time

from asqlite import ProxiedConnection
from sqlite3 import Row


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
            user_uploaded_id: str,
            size: int,
    ) -> None:

        current_time = int(time.time())

        async with connection.transaction():
            await connection.execute(
                """
                INSERT INTO files
                (file_id, file_cluster_id, user_uploaded_id, size, uploaded_at) VALUES (?, ?, ?, ?, ?)
                """,
                file_id, cluster_id, user_uploaded_id, size, current_time
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