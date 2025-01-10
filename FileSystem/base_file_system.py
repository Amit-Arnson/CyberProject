import os
import asyncio
import aiofiles
import asqlite
from FileSystem.file_extension import Extension


class InvalidExtension(Exception):
    """Use this class to throw errors when an unacceptable extension is used"""
    def __init__(self):
        super().__init__("Invalid file extension")


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
        :param name: the name (or ID) of the file
        :param path: the directory where you want it saved
        :return: the full path of the file
        """

        # combines the name (ID) of the file with the directory it should be saved under
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
