import os
import asyncio
import time

import aiofiles
import asqlite
from FileSystem.file_extension import Extension

from queries import FileSystem


class System:
    """
    if you change the default names of things in this class, make sure to ALWAYS build the class
    using those names.
    if you are unsure, do not pass any arguments unless they are required.
    """
    def __init__(self, db_pool: asqlite.Pool, directory: str = "audio_files", cluster_size: int = 100):
        self.db_pool = db_pool

        os.makedirs(directory, exist_ok=True)

        self.main_directory = directory
        self.cluster_size = cluster_size

    @staticmethod
    def _create_unique_id(random_bytes_length: int = 8) -> str:
        # to ensure a unique ID, we can use the current time with randomized bytes at the end
        current_time_hex = time.time().hex()

        random_bytes_hex = os.urandom(random_bytes_length).hex()

        # we hex both of them since cluster ID is a string that is basically a dir

        unique_cluster_id = f"{current_time_hex}_{random_bytes_hex}"

        return unique_cluster_id

    async def _create_file_id(self) -> str:
        """:returns: a unique file ID that doesnt exist in the database yet"""

        unique_file_id = ""
        exists = True
        while exists:

            unique_file_id = self._create_unique_id()

            async with self.db_pool.acquire() as connection:
                exists = FileSystem.does_file_exist(connection=connection, file_id=unique_file_id)

        # this error should NEVER raise. if it does, fuck.
        if not unique_file_id:
            raise Exception("new achievement: how did we get here?")

        return unique_file_id

    async def _create_cluster_id(self) -> str:
        """:returns: a unique cluster ID that doesnt exist in the database yet"""

        unique_cluster_id = ""
        exists = True
        while exists:

            unique_cluster_id = self._create_unique_id()

            async with self.db_pool.acquire() as connection:
                exists = FileSystem.does_cluster_exist(connection=connection, cluster_id=unique_cluster_id)

        # this error should NEVER raise. if it does, fuck.
        if not unique_cluster_id:
            raise Exception("new achievement: how did we get here?")

        return unique_cluster_id

    async def _create_new_cluster(self) -> str:
        """:returns: name (ID) of the cluster"""

        # 1) generate cluster ID
        cluster_id = await self._create_cluster_id()

        # 2) save cluster
        async with self.db_pool.acquire() as connection:
            await FileSystem.create_new_cluster(connection=connection, cluster_id=cluster_id)

        # 3) create cluster under dir (main_dir/cluster_id)
        cluster_dir = os.path.join(self.main_directory, cluster_id)

        # creates the cluster dir under the parent directory.
        os.makedirs(cluster_dir)

        # 4) return cluster ID
        return cluster_dir

    async def _find_free_cluster(self) -> str:
        """:returns: cluster's full directory"""

        async with self.db_pool.acquire() as connection:
            free_cluster_id = FileSystem.find_free_cluster(connection, max_size=self.cluster_size)

        if not free_cluster_id:
            free_cluster_id = await self._create_new_cluster()

        return os.path.join(self.main_directory, free_cluster_id)

    # todo: create User object and change upload ID to User Object (which will contain ID, along other things)
    async def save(self, file: "BaseFile", uploaded_by_id: str) -> tuple[str, str]:
        """
        accepts a file and saves it to an available cluster.
        a file will be saved under "directory"/"file ID", as well as in the database under the "files" table (base case for files)

        to save the file to an image/audio file table, it must be done manually.

        :param file: the file that you want to save
        :param uploaded_by_id: the User ID that uploaded the file
        :returns: tuple[file ID (name), saved directory (main_dir/cluster_id)]
        """

        # finds a free cluster's directory path. if a free cluster does not exist, it creates on.
        save_under = await self._find_free_cluster()

        # TODO: finish working on save
        # todo: see if maybe automatic save to image/audio file tables. check doc-string for reference


# main_dir/cluster_id/file_id


class BaseFile:
    """
        A class that represents a file and provides methods to load, save, and manipulate it.
        use await File(...).load() in order to access the file

        Attributes:
            path (str): The path to the file.
            _file (bytes): The file's binary content.
            file_type (str): The MIME type of the file.
            file_extension (str): The file's extension.
        """

    def __init__(self, file_path: str):
        self.path = file_path

        # these are all loaded with await self.load()
        self._file: bytes = b""
        self.file_type: str = ""
        self.file_extension: str = ""

    async def load(self) -> None:
        """
        this function initially loads the file from a given path
        """

        # the reason we check both path AND _file, is because we want the extensions to be loaded when
        # using File.from_bytes(...)
        if not self.path and not self._file:
            return

        # read bytes if a path is passed
        if self.path:
            async with aiofiles.open(self.path, "rb") as file:
                self._file = await file.read()

        self.file_type, self.file_extension = Extension(self._file).get_file_type()

    async def save(self, name: str, path: str) -> str:
        """
        :param name: the name (or ID) of the file. it will replace any current file name with the given one
        :param path: the directory where you want it saved
        :return: the full path of the file
        """

        # combines the name (ID) of the file with the directory it should be saved under
        # main_dir/cluster_id/file_name
        path = os.path.join(path, name)

        if not self._file:
            raise ValueError("No content to save. Load or set the file content first.")

        # write bytes
        async with aiofiles.open(path, "wb") as file:
            await file.write(self._file)

        return path

    @staticmethod
    async def from_bytes(file: bytes) -> "BaseFile":
        """
        creates a File object from inputted file bytes
        """
        cls_file = BaseFile(
            file_path=""
        )

        cls_file._file = file

        # this is in order to load the extension and file type
        await cls_file.load()

        return cls_file

    def __bytes__(self) -> bytes:
        return self._file

    def __len__(self) -> int:
        """the length of the files in bytes"""
        return len(self._file)

    def __str__(self) -> str:
        """returns the 'type/extension' of the file"""
        return f"{self.file_type}/{self.file_extension}"
