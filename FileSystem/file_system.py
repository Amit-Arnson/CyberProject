import os
import asyncio
import aiofiles
import aiosqlite

class System:
    """
    if you change the default names of things in this class, make sure to ALWAYS build the class
    using those names.
    if you are unsure, do not pass any arguments unless they are required.
    """
    def __init__(self, directory: str = "audio_files", cluster_size: int = 100):
        os.makedirs(directory, exist_ok=True)
        self.cluster_size = cluster_size




# main_dir/cluster_id/file_id


class File:
    def __init__(self, file_path: str):
        self.path = file_path
        self._file: bytes

        event_loop = asyncio.get_event_loop()
        event_loop.run_in_executor(None, self._load)

    async def _load(self) -> None:
        async with aiofiles.open(self.path, "rb") as file:
            self._file = await file.read()

    def __bytes__(self) -> bytes:
        return self._file
