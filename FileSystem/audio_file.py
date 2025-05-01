from FileSystem.base_file_system import BaseFile


# todo: check if i still need this class, as i do things based on chunks now instead of fully loaded files
class AudioFile(BaseFile):
    """a child class of BaseFile designed to limit files to certain extensions and size"""
    def __init__(self, file_path: str):
        super().__init__(file_path=file_path)
        self._allowed_extensions = (
            "wav", "mp3", "ogg"
        )

        # 10 MB
        self._max_size: int = 10000000

        # the length of the song in seconds (or milliseconds, dont know yet)
        self._length: int | None = None

    # it is async because it might need to .load() the file
    async def get_length(self) -> int:
        if self._length:
            return self._length

        # todo: implement logic
        return 0

    def allowed_size(self) -> bool:
        """checks if the size of the file is less than the max file size that is allowed"""
        return len(self) <= self._max_size

    def allowed_extension(self) -> bool:
        """checks if the file's extension exists in the allowed extensions"""
        return self.file_extension in self._allowed_extensions

    def is_allowed(self) -> bool:
        """
        checks if the file adheres to the size and extension limitations
        """
        return all(
            (
             self.allowed_size(),
             self.allowed_extension()
            )
        )
