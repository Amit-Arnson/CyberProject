import asqlite
import asyncio

from asqlite import Cursor


class CreateTables:
    def __init__(self, database: str):
        self.database = database

    async def aio_init(self):
        async with asqlite.connect(self.database) as connection:
            async with connection.cursor() as cursor:
                await self._create_clusters(cursor)
                await self._create_users(cursor)
                # ...

                await connection.commit()

    # all of these methods will create tables
    @staticmethod
    async def _create_clusters(cursor: Cursor):
        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS clusters (
                id INTEGER PRIMARY KEY,
                max_size INTEGER NOT NULL,
                current_size INTEGER NOT NULL DEFAULT 0
            );
            """
        )

    @staticmethod
    async def _create_users(cursor: Cursor):
        print(type(cursor))
        await cursor.execute(
            """
                        CREATE TABLE IF NOT EXISTS users (
                            user_id INTEGER PRIMARY KEY,
                            username TEXT NOT NULL,
                            display_name TEXT NOT NULL,
                            password TEXT NOT NULL,
                            salt BLOB NOT NULL
                        );
            """
        )


if __name__ == "__main__":
    tables = CreateTables(f"database.db")
    asyncio.run(tables.aio_init())
