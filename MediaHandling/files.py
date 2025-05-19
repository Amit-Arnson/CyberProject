from MediaHandling.ffmpeg import FFmpegImage, FFmpegAudio, compress

import aiofiles.os as aos
import os


# todo: think of a more fitting name for the file (like, replace files.py with a better name)
async def compress_and_replace(
        file_extension: str,
        compressed_extension: str,
        directory: str,
        input_file: str,
        ffmpeg_flags: FFmpegAudio | FFmpegImage | dict[str, str]
) -> int:
    """
    MediaHandling the input file, save it to a temporary file, and replace the original file with the compressed version.
    note: the file/compressed file extension is not necessarily the same as the codec (such as aac_mf, which is the codec
     and the extension is still .aac) and thus you are required to still enter the file extension and the compressed file
     extension

    :returns: the size (in bytes) of the compressed file
    """

    # if it isn't a dictionary, it is either FFmpegAudio or FFmpegImage which we can turn into a dict
    if not isinstance(ffmpeg_flags, dict):
        ffmpeg_flags: dict[str, str] = ffmpeg_flags.to_dict()

    input_path = os.path.join(directory, f"{input_file}.{file_extension}")

    # output for the compression
    temp_file = os.path.join(directory, f"temp_{input_file}.{compressed_extension}")

    try:
        # MediaHandling the file
        await compress(
            input_file=input_path,
            output_file=temp_file,
            flag_values=ffmpeg_flags
        )

        # despite path.exists() NOT being async, it shouldn't matter all that much because it isn't very resource-intensive
        if os.path.exists(input_path):
            # async deletes the original file, as it isn't needed anymore
            await aos.remove(input_path)

        new_file = os.path.join(directory, f"{input_file}.{compressed_extension}")

        # async rename temporary file
        await aos.rename(temp_file, new_file)

        file_info = await aos.stat(new_file)
        new_file_size = file_info.st_size

        return new_file_size
    except Exception as e:
        if os.path.exists(temp_file):
            os.remove(temp_file)  # Clean up temp file in case of failure

        raise e
