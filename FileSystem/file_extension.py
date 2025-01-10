# magic numbers are a few bytes (usually between 8-16) at the start of the file that hint at the extension type of the file
magic_numbers: dict[bytes, tuple[str, str]] = {
    # Image formats
    b'\xff\xd8\xff': ('image', 'jpeg'),  # JPEG
    b'\x89PNG\r\n\x1a\n': ('image', 'png'),  # PNG
    b'GIF87a': ('image', 'gif'),  # GIF (old version)
    b'GIF89a': ('image', 'gif'),  # GIF (new version)
    b'\x52\x49\x46\x46\x57\x45\x42\x50': ('image', 'webp'),  # WebP (based on the RIFF format)
    b'\x42\x4D': ('image', 'bmp'),  # BMP (Windows bitmap)
    b'\x89WEBP': ('image', 'webp'),  # WebP (based on the WEBP signature)

    # Audio formats
    b'\x52\x49\x46\x46\x57\x41\x56\x45': ('audio', 'wav'),  # WAV (RIFF header)
    b'ID3': ('audio', 'mp3'),  # MP3
    b'\x66\x4C\x61\x43': ('audio', 'flac'),  # FLAC
    b'OggS': ('audio', 'ogg'),  # OGG
    b'\x66\x74\x79\x70\x4D\x34\x41': ('audio', 'm4a'),  # M4A (MP4 audio)
    b'\x46\x4F\x52\x4D': ('audio', 'aiff'),  # AIFF
    b'\x30\x26\xB2\x75\x8E\x66\xCF': ('audio', 'wma'),  # WMA

    # Video formats
    b'\x00\x00\x00\x18\x66\x74\x79\x70': ('video', 'mp4'),  # MP4 video
    b'\x1A\x45\xDF\xA3': ('video', 'mkv'),  # MKV (Matroska video)
}

# https://en.wikipedia.org/wiki/List_of_file_signatures
# todo: make sure that extensions like webp are handled correctly, as according to the wiki it may have a different format

# todo: magic numbers can be faked. add further validation for file checking.


class Extension:
    def __init__(self, file: bytes):
        self._file = file

    def get_file_type(self) -> tuple[str, str]:
        """
        Determines the file type based on its magic number.
        :return: the type and extension of the file in a tuple
        """

        for magic, file_type in magic_numbers.items():
            if self._file.startswith(magic):
                return file_type

        # returning ("", "") is this method's way of returning None while still returning tuple[str, str]
        return "", ""
