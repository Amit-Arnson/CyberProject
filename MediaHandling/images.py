from MediaHandling.files import compress_and_replace
from MediaHandling.ffmpeg import FFmpegImage, Codec


async def compress_to_webp(
        file_extension: str,
        directory: str,
        input_file: str,
) -> tuple[int, str]:
    """
    Compresses the input image file to a .webp output file, using libwebp as the -c:a flag, using FFmpeg asynchronously, and also replaces the old
    uncompressed file with the new compressed file *using MediaHandling.files.compress_and_replace*

    :returns: the new size of the compressed file (in bytes) and the output file's extension ("webp")
    """

    compressed_extension = "webp"

    extra_compression_ffmpeg_values: dict[str, ...] = {
        "-compression_level": 6,
        "-preset": "text",
        "-map_metadata": -1,
        "-map_chapters": -1,
        "-lossless": 0
    }

    ffmpeg_values = FFmpegImage(
        codec=Codec.WEBP,
        quality=100,
    ).to_dict(
        extra=extra_compression_ffmpeg_values
    )

    total_size = await compress_and_replace(
        file_extension=file_extension,
        compressed_extension=compressed_extension,
        input_file=input_file,
        directory=directory,
        ffmpeg_flags=ffmpeg_values
    )

    return total_size, compressed_extension


async def compress_to_low_res_webp(
        file_extension: str,
        directory: str,
        input_file: str,
) -> tuple[int, str]:
    """
    Compresses the input image file to a .webp output file, using libwebp as the -c:a flag, using FFmpeg asynchronously, and also replaces the old
    uncompressed file with the new compressed file *using MediaHandling.files.compress_and_replace*

    this compression's flags reduce the size of the file drastically, but also reduces quality.

    :returns: the new size of the compressed file (in bytes) and the output file's extension ("webp")
    """

    compressed_extension = "webp"

    ffmpeg_values = FFmpegImage(
        codec=Codec.WEBP,
        quality=0
    )

    extra_compression_ffmpeg_values: dict[str, ...] = {
        "-compression_level": 6,
        "-lossless": 1,
        "-map_metadata": -1,
        "-map_chapters": -1,
        "-preset": "drawing"
    }

    ffmpeg_values.to_dict(
        extra=extra_compression_ffmpeg_values
    )

    total_size = await compress_and_replace(
        file_extension=file_extension,
        compressed_extension=compressed_extension,
        input_file=input_file,
        directory=directory,
        ffmpeg_flags=ffmpeg_values
    )

    return total_size, compressed_extension
