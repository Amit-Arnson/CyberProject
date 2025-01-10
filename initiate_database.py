import asqlite
import asyncio


class CreateTables:
    def __init__(self, database: str):
        self.database = database

    async def aio_init(self):
        async with asqlite.connect(self.database) as connection:
            async with connection.cursor() as cursor:
                await self._create_clusters(cursor)
                # ...

                await connection.commit()

    # all of these methods will create tables
    @staticmethod
    async def _create_clusters(cursor: asqlite.Cursor):
        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS clusters (
                id INTEGER PRIMARY KEY,
                max_size INTEGER NOT NULL,
                current_size INTEGER NOT NULL DEFAULT 0
            );
            """
        )


if __name__ == "__main__":
    tables = CreateTables(f"database.db")
    asyncio.run(tables.aio_init())
