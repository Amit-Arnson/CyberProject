# this file is used as a way to organize all the needed SQL queries

from asqlite import ProxiedConnection


class User:
    @staticmethod
    async def create_user(connection: ProxiedConnection, user_id, username: str, display_name: str, password: str, salt: bytes) -> None:
        await connection.execute(
            "INSERT INTO users (user_id, username, display_name, password, salt) VALUES (?, ?, ?, ?, ?)",
            user_id, username, display_name, password, salt
        )