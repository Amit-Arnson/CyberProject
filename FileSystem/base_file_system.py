import base64
import logging
import os
import asyncio
import time

import aiofiles
import asqlite

from Utils.chunk import FileTypes
from FileSystem.file_extension import Extension

from queries import FileSystem

from Compress.ffmpeg import is_valid_file
from Compress.audio import compress_to_aac
from Compress.images import compress_to_webp, compress_to_low_res_webp

from Errors.raised_errors import InvalidCodec


class System:
    def __init__(self, db_pool: asqlite.Pool):
        self.db_pool = db_pool

        # setting default values inside the __init__ so that its clear that these shouldn't just be chosen randomly.
        # to change their value, check the set_... functions.
        self._main_directory = "SavedFiles"
        self._cluster_size = 100

    # I have created set_... for directory and cluster size so that it is clear that these values are not "just" part of the constructor.
    # changing these values means that the files will be saved in different places, and that the max files saved in one place will be changed.
    # if that is the behaviour you want, you can use these functions to change the values.
    def set_default_directory(self, directory: str):
        """set the main directory to one of your choosing. this is where the clusters will be created"""
        self._main_directory = directory

    def set_max_cluster_size(self, max_cluster_size: int):
        """set the maximum amount of files that can be saved under each cluster"""
        self._cluster_size = max_cluster_size

    # we don't want it attempting to create directories just by calling the class, so I made it into a separate function
    def initialize(self):
        """create the directory which every file will be saved under"""

        # only attempt to make the directory if it doesn't exist yet
        if not os.path.exists(self._main_directory):
            os.makedirs(self._main_directory, exist_ok=True)
        else:
            # ansi color for blue. logging.info didn't work for some reason, so I just use a normal print here.
            blue_text = '\033[34m'

            # resets the console color back.
            ansi_break = '\x1b[0m'
            print(f"{blue_text}INFO: THE DIRECTORY \"{self._main_directory}\" ALREADY EXISTS.{ansi_break}")

    @staticmethod
    def _create_unique_id(random_bytes_length: int = 8) -> str:
        # to ensure a unique ID, we can use the current time with randomized bytes at the end
        current_time_hex = time.time().hex()

        random_bytes_hex = os.urandom(random_bytes_length).hex()

        # we hex both of them since cluster ID is a string that is basically a dir

        unique_id = f"{random_bytes_hex}_{current_time_hex}".encode()

        padding_length = (3 - len(unique_id) % 3) % 3  # Calculate how many bytes to add
        b64_padding_remove = b"0" * padding_length

        unique_id = base64.b64encode(unique_id + b64_padding_remove).decode()

        return unique_id

    async def _create_file_id(self) -> str:
        """:returns: a unique file ID that doesnt exist in the database yet"""

        unique_file_id = ""
        exists = True
        while exists:
            unique_file_id = self._create_unique_id()

            async with self.db_pool.acquire() as connection:
                exists = await FileSystem.does_file_exist(connection=connection, file_id=unique_file_id)

        if not unique_file_id:
            raise Exception("unique file ID failed to be created in BaseFileSystem")

        return unique_file_id

    async def _create_cluster_id(self) -> str:
        """:returns: a unique cluster ID that doesnt exist in the database yet"""

        unique_cluster_id = ""
        exists = True
        while exists:
            unique_cluster_id = self._create_unique_id()

            async with self.db_pool.acquire() as connection:
                exists = await FileSystem.does_cluster_exist(connection=connection, cluster_id=unique_cluster_id)

        if not unique_cluster_id:
            raise Exception("unique cluster ID failed to be created in BaseFileSystem")

        return unique_cluster_id

    async def _create_new_cluster(self) -> str:
        """:returns: name (ID) of the cluster"""

        # 1) generate cluster ID
        cluster_id = await self._create_cluster_id()

        # 2) save cluster
        async with self.db_pool.acquire() as connection:
            await FileSystem.create_new_cluster(connection=connection, cluster_id=cluster_id)

        # 3) create cluster under dir (main_dir/cluster_id)
        cluster_dir = os.path.join(self._main_directory, cluster_id)

        # creates the cluster dir under the parent directory.
        os.makedirs(cluster_dir)

        # 4) return cluster ID
        return cluster_id

    async def _find_free_cluster(self) -> tuple[str, str]:
        """:returns: tuple[cluster's full directory (main_dir/cluster_id), cluster ID]"""

        async with self.db_pool.acquire() as connection:
            free_cluster_id = await FileSystem.find_free_cluster(connection, max_size=self._cluster_size)

        if not free_cluster_id:
            free_cluster_id = await self._create_new_cluster()

        return os.path.join(self._main_directory, free_cluster_id), free_cluster_id

    async def get_id(self) -> tuple[str, str, str]:
        """
        creates/retrieves the save dir (which is the path of main_dir/cluster_id), a free cluster ID and creates a new file ID
        :returns: tuple[save directory, cluster ID, file ID]
        """

        # finds a free cluster's directory path. if a free cluster does not exist, it creates on.
        save_directory, cluster_id = await self._find_free_cluster()

        # create a random file ID to save the file under
        file_id = await self._create_file_id()

        print(f"created IDs: {save_directory}/{file_id}")

        return save_directory, cluster_id, file_id

    @staticmethod
    async def save_stream(chunk: "FileChunk", uploaded_by_id: str, is_last_chunk: bool,
                          chunk_content_type: str | FileTypes) -> dict[str, str | int] | tuple[str, str]:
        # due to how chunks are processed before arriving here, all the chunks should have a valid file extension
        if not chunk.file_extension:
            logging.error(f"chunk file ID {chunk.file_id} #{chunk.chunk_number} is missing file extension")
            raise InvalidCodec(f"Invalid file format given")

        if isinstance(chunk_content_type, FileTypes):
            chunk_content_type: str = chunk_content_type.value

        try:
            # saves the file under main_dir/cluster_dir/file_id
            await chunk.save()
        except Exception as e:
            print(f"error: {e}: save dir: {chunk.save_directory}, file ID: {chunk.file_id}, user ID: {uploaded_by_id}")
            raise e

        if is_last_chunk:
            final_file_format: str = chunk.file_extension
            final_file_id = f"{chunk.file_id}.{final_file_format}"

            # if the file was not compressed, we just use the total_size that we have in the FileChunk
            total_size = chunk.total_file_size

            final_file_path = os.path.join(chunk.save_directory, final_file_id)

            # we check that the file's integrity is valid and that there is no corrupt data
            file_is_valid: bool = await is_valid_file(final_file_path)

            if not file_is_valid:
                raise InvalidCodec("Invalid file given and was rejected")

            compressed_extension = None
            compress_dict = {
                "file_extension": chunk.file_extension,
                "input_file": f"{chunk.file_id}",
                "directory": chunk.save_directory
            }

            if chunk.file_type == "audio" and chunk_content_type == FileTypes.AUDIO.value:
                # we change the total size to the new size of the compressed file
                total_size, compressed_extension = await compress_to_aac(
                    **compress_dict
                )

            elif chunk.file_type == "image" and chunk_content_type == FileTypes.SHEET.value:
                total_size, compressed_extension = await compress_to_webp(
                    **compress_dict
                )

            elif chunk.file_type == "image" and chunk_content_type == FileTypes.COVER.value:
                total_size, compressed_extension = await compress_to_low_res_webp(
                    **compress_dict
                )

            if compressed_extension:
                final_file_id = f"{chunk.file_id}.{compressed_extension}"
                final_file_format = compressed_extension

            # returns the DB parameters for base_file
            return {
                "cluster_id": chunk.cluster_id,
                "file_id": final_file_id,
                "user_uploaded_id": uploaded_by_id,
                "size": total_size,
                "raw_file_id": chunk.file_id,
                "file_format": final_file_format
            }
        else:
            return chunk.file_id, chunk.save_directory


class FileChunk:
    """
    A class that represents a small part of a file (the "chunk" of a file), and is able to store the chunk's metadata
    in order to easily handle it
    """

    def __init__(
            self,
            current_file_size: int,
            chunk: bytes,
            file_id: str,
            cluster_id: str,
            save_directory: str,
            chunk_number: int,
            asyncio_lock: asyncio.Lock,
            file_extension: str = None,
            out_of_order_chunks: list = None
    ):
        self._lock = asyncio_lock
        self.chunk = chunk

        if out_of_order_chunks:
            out_of_order_combined = b"".join(out_of_order_chunks)
            self.chunk += out_of_order_combined

        self.file_id = file_id
        self.cluster_id = cluster_id
        self.save_directory = save_directory
        self.chunk_number = chunk_number

        self.size = len(chunk)

        self.total_file_size = current_file_size + self.size

        # both file_type and extension are lower case for consistency
        self._given_file_extension = file_extension.lower() if file_extension else None

        self.file_type, self.file_extension = self._get_chunk_type()

    # if a file extension doesn't appear in this dict, it means that the server does not accept it as a possible type
    # and therefor should not be saved to the server
    def _get_chunk_type(self) -> tuple[str, str] | tuple[None, None | str]:
        # if it isn't the first chunk (where the magic numbers are usually saved), there is no need to check for the
        # file type and extension
        if self.chunk_number != 1:
            mime_to_type: dict[str, str] = {
                "jpeg": "image",
                "png": "image",
                "gif": "image",
                "webp": "image",

                "wav": "audio",
                "mp3": "audio",
                "flac": "audio",
                "ogg": "audio",
                "m4a": "audio",
                "aiff": "audio",
                "wma": "audio"
            }

            return mime_to_type.get(self._given_file_extension), self._given_file_extension

        extensions: dict[tuple[str, tuple[int], bytes] | tuple[str, tuple[tuple[int], bytes], ...], tuple[str, str]] = {
            # Image formats
            ("single", (0, 3), b'\xff\xd8\xff'): ('image', 'jpeg'),  # JPEG
            ("single", (0, 8), b'\x89PNG\r\n\x1a\n'): ('image', 'png'),  # PNG
            ("single", (0, 6), b'GIF87a'): ('image', 'gif'),  # GIF (old version)
            ("single", (0, 6), b'GIF89a'): ('image', 'gif'),  # GIF (new version)
            ("split", ((0, 4), b'\x52\x49\x46\x46'), ((8, 12), b'\x57\x45\x42\x50')): ('image', 'webp'),  # WebP
            ("single", (0, 5), b'\x89WEBP'): ('image', 'webp'),  # WebP (alternative)

            # Audio formats
            ("split", ((0, 4), b'\x52\x49\x46\x46'), ((8, 12), b'\x57\x41\x56\x45')): ('audio', 'wav'),  # WAV
            ("single", (0, 3), b'ID3'): ('audio', 'mp3'),  # MP3 with ID3 metadata
            ("single", (0, 2), b'\xFF\xFB'): ('audio', 'mp3'),  # MP3 (frame header sync word)
            ("single", (0, 2), b'\xFF\xF3'): ('audio', 'mp3'),  # MP3 (MPEG-2 Layer III)
            ("single", (0, 4), b'\x66\x4C\x61\x43'): ('audio', 'flac'),  # FLAC
            ("single", (0, 4), b'OggS'): ('audio', 'ogg'),  # OGG
            ("single", (0, 7), b'\x66\x74\x79\x70\x4D\x34\x41'): ('audio', 'm4a'),  # M4A
            ("single", (0, 4), b'\x46\x4F\x52\x4D'): ('audio', 'aiff'),  # AIFF
            ("single", (0, 7), b'\x30\x26\xB2\x75\x8E\x66\xCF'): ('audio', 'wma'),  # WMA
            ("single", (0, 2), b'\xFF\xF1'): ('audio', 'aac'),  # ADTS AAC (raw AAC stream)
            ("single", (0, 4), b'\x00\x00\x00\x18'): ('audio', 'aac'), # MP4/M4A container with AAC audio (ftyp box start)

        }

        for magic, file_type in extensions.items():
            # this gets the type of magic number "type" that we need to look for
            # single - this means that it is a few bytes at the very start of the file (meaning we can use "startswith")
            # split - this means that it is like "magic-bytes... other data... magic-bytes", meaning we need to look
            # over multiple areas of the chunk
            magic_index_type = magic[0]

            if magic_index_type == "split":
                matches = True

                # creates a tuple without the "magic type" in it, so that it can iterate over the tuple
                new_magic_tuple: tuple[tuple[int, int], bytes] = magic[1::]

                for indexes, magic_value_bytes in new_magic_tuple:
                    if not self.chunk[indexes[0]:indexes[1]] == magic_value_bytes:
                        matches = False
                        break

                if matches:
                    return file_type
            else:
                # gets the actual magic bytes themselves (magic type, (index, index), magic bytes)
                magic_bytes: bytes = magic[2]

                # In case of a "single"
                if self.chunk.startswith(magic_bytes):
                    return file_type

        return None, None

    async def _write(self, path: str):
        async with aiofiles.open(path, "ab") as file:
            await file.write(self.chunk)

    async def save(self, last_chunk_number: int | None = None) -> str:
        # combines the name (ID) of the file with the directory it should be saved under
        # main_dir/cluster_id/file_name
        path: str = os.path.join(self.save_directory, self.file_id + f'.{self.file_extension}')

        # if we have a last_chunk_number available, and it is actually the previous number, OR if we don't have a
        # last_chunk_number, it will be True (this is because, if we don't have a last chunk available we cant "insert" it
        # into a position, so we assume it is in position already). otherwise, we say the chunks are unordered
        chunk_in_order = True if last_chunk_number and last_chunk_number + 1 == self.chunk_number or not last_chunk_number else False

        try:
            if chunk_in_order:
                # we need to lock the file while it is being written to so that multiple chunks do not try to
                # override each-other (despite it being in "append bytes" mode)
                async with self._lock:
                    await self._write(path)
            else:
                # all out of order chunk fixes happen before this step, so if it is still out of order there is a bigger
                # issue at play
                raise Exception(f"out of order chunks: {self.file_id}")
        except Exception as e:
            logging.error(e, exc_info=True)
            raise Exception(f"failed to save file \"{path}\" under file.save() (FileChunk)")

        return path


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
        """
        after creating the object, use .load() to load the bytes and extensions.
        to create an instance without the file_path, use BaseFile.from_bytes(...) to create the object.
        """
        self.path = file_path

        # these are all loaded with await self.load()
        self._file: bytes = b""
        self.file_type: str = ""
        self.file_extension: str = ""

        # a simple check to see if a file is initialized (self.load()). this can be used for validation checking
        # when calling functions that require the loaded file.
        self.loaded = False

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

        # set the loaded trigger to True after loading the file.
        self.loaded = True

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

        try:
            # write bytes
            async with aiofiles.open(path, "wb") as file:
                await file.write(self._file)
        except Exception as e:
            logging.error(e, exc_info=True)

            # todo: check code consistency to see if we need an error class instead of base exception. (error code: 500)
            raise Exception(f"failed to save file \"{path}\" under file.save() (BaseFile)")

        return path

    @staticmethod
    async def from_bytes(file: bytes) -> "BaseFile":
        """
        creates a File object from inputted file bytes.
        This function calls .load() for you, therefore you do not need to load it yourself.
        """

        cls_file = BaseFile(file_path="")
        cls_file._file = file

        # this is in order to load the extension and file type
        await cls_file.load()

        return cls_file

    def size(self):
        """an alternative method to len(). returns the size of the file in bytes"""
        return self.__len__()

    def __bytes__(self) -> bytes:
        return self._file

    def __len__(self) -> int:
        """the length of the files in bytes"""
        return len(self._file)

    def __str__(self) -> str:
        """returns the 'type/extension' of the file"""
        return f"{self.file_type}/{self.file_extension}"
