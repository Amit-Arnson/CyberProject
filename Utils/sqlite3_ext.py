import asqlite


import os

spell_fix_extension = os.path.abspath("./Sqlite3Extensions/spellfix.dll")


def init_connection(conn):
    conn.enable_load_extension(True)
    conn.execute(f"SELECT load_extension('{spell_fix_extension}');")


# Create the connection pool with the init function
async def create_connection_pool(database: str):
    pool = await asqlite.create_pool(
        database,
        init=init_connection,
        size=10
    )
    return pool
