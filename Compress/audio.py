from Compress.files import compress_and_replace
from Compress.ffmpeg import FFmpegAudio, Codec


async def compress_to_acc(
        file_extension: str,
        directory: str,
        input_file: str,
) -> tuple[int, str]:
    """
    Compresses the input audio file to a .aac output file, using aac_mf as the -c:a flag, using FFmpeg asynchronously, and also replaces the old
    uncompressed file with the new compressed file *using Compress.files.compress_and_replace*

    :returns: the new size of the compressed file (in bytes) and the output file's extension ("aac")
    """

    # a .aac file extension is one of the best extensions for making large files small whilst keeping
    # the audio quality
    compressed_extension = "aac"

    ffmpeg_values = FFmpegAudio(
        codec=Codec.AAC_MF,
        bitrate="64k"
    )

    total_size = await compress_and_replace(
        file_extension=file_extension,
        compressed_extension=compressed_extension,
        input_file=input_file,
        directory=directory,
        ffmpeg_flags=ffmpeg_values
    )

    return total_size, compressed_extension
