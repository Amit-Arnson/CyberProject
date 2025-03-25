from Compress.files import compress_and_replace
from Compress.ffmpeg import FFmpegAudio, Codec

import asyncio


async def compress_to_aac(
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
        bitrate="48k",
    ).to_dict(
        {
            "-map_metadata": -1,
            "-map": "0:a"
        }
    )

    total_size = await compress_and_replace(
        file_extension=file_extension,
        compressed_extension=compressed_extension,
        input_file=input_file,
        directory=directory,
        ffmpeg_flags=ffmpeg_values
    )

    return total_size, compressed_extension


async def get_audio_length(
        input_file: str,
) -> int:
    """
    Gets the duration of an audio file in milliseconds.
    """

    ffprobe_exe = r".\ffmpeg\bin\ffprobe.exe"  # Update this to the correct path

    try:
        # Build the ffprobe command
        command = [
            ffprobe_exe,
            "-i", input_file,
            "-show_entries",
            "format=duration",  # Extract the duration only
            "-v", "quiet",
            "-of", "csv=p=0"
        ]

        # Run ffprobe asynchronously
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        # If ffprobe fails, log the error and return -1
        if process.returncode != 0:
            raise Exception(f"ffprobe error: {stderr.decode().strip()}")

        # Parse the duration (in seconds) from stdout and convert to milliseconds
        duration_seconds = float(stdout.decode().strip())
        return int(duration_seconds * 1000)

    except FileNotFoundError:
        raise "ffprobe executable not found. Make sure it's in the specified path."
    except Exception as e:
        raise e
