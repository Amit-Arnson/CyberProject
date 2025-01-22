# this file is used as a way to organize all the needed SQL queries

from asqlite import ProxiedConnection
from sqlite3 import Row


class User:
    @staticmethod
    async def create_user(connection: ProxiedConnection, user_id: str, username: str, display_name: str, password: str, salt: bytes) -> None:
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
