# magic numbers are a few bytes (usually between 8-16) at the start of the file that hint at the extension type of the file
magic_numbers: dict[bytes, tuple[str, str]] = {
    b'\xff\xd8\xff': ('image', 'jpeg'),
    b'\x89PNG\r\n\x1a\n': ('image', 'png'),
    b'GIF87a': ('image', 'gif'),
    b'GIF89a': ('image', 'gif'),
    b'RIFF': ('audio', 'wav'),
    b'ID3': ('audio', 'mp3'),
    b'\x66\x4C\x61\x43': ('audio', 'flac'),
    b'OggS': ('audio', 'ogg'),
    b'\x66\x74\x79\x70\x4D\x34\x41': ('audio', 'm4a'),
    b'\x46\x4F\x52\x4D': ('audio', 'aiff'),
    b'\x30\x26\xB2\x75\x8E\x66\xCF': ('audio', 'wma')
}


class Extension:
    def __init__(self, file: bytes):
        self._file = file

    def get_file_type(self) -> tuple[str, str] | None:
        """
        Determines the file type based on its magic number.
        :return: the type and extension of the file in a tuple
        """

        for magic, file_type in magic_numbers.items():
            if self._file.startswith(magic):
                return file_type

        return None
