from Compress.files import compress_and_replace
from Compress.ffmpeg import FFmpegImage, Codec


async def compress_to_webp(
        file_extension: str,
        directory: str,
        input_file: str,
) -> tuple[int, str]:
    """
    Compresses the input image file to a .webp output file, using libwebp as the -c:a flag, using FFmpeg asynchronously, and also replaces the old
    uncompressed file with the new compressed file *using Compress.files.compress_and_replace*

    :returns: the new size of the compressed file (in bytes) and the output file's extension ("webp")
    """

    compressed_extension = "webp"

    ffmpeg_values = FFmpegImage(
        codec=Codec.WEBP,
        quality=2
    )

    total_size = await compress_and_replace(
        file_extension=file_extension,
        compressed_extension=compressed_extension,
        input_file=input_file,
        directory=directory,
        ffmpeg_flags=ffmpeg_values
    )

    return total_size, compressed_extension
