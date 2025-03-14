import os
import asyncio

import aiofiles.os as aos

import logging


import asyncio


async def is_valid_file(file_path: str) -> bool:
    """
    Validates a file's integrity. If the file is corrupted or uses false data, this function will return False, else True
    """

    ffprobe_cmd = r".\ffmpeg\bin\ffprobe.exe"  # Update this to the correct path

    try:
        # Build the ffprobe command
        command = [
            ffprobe_cmd,
            "-show_format",      # Check file format
            "-show_streams",     # Check streams
            file_path            # The file to validate
        ]

        # Run ffprobe asynchronously
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        # If ffprobe fails, stderr will contain an error message
        if process.returncode != 0:
            return False

        # If everything is okay
        return True

    except FileNotFoundError:
        print("ffprobe executable not found. Make sure it's in the specified path.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False


async def compress_audio(input_file: str, output_file: str, **kwargs):
    """
    Compresses the input audio file to the specified output file using FFmpeg asynchronously.
    """

    # Ensure FFmpeg is in the system PATH
    ffmpeg_cmd = r".\ffmpeg\bin\ffmpeg.exe"

    if not os.path.exists(ffmpeg_cmd):
        raise Exception(f"Couldn't find the FFmpeg executable in {ffmpeg_cmd}")

    try:
        # Command to convert the audio file using FFmpeg
        command = [
            ffmpeg_cmd,
            "-loglevel", "quiet",  # Suppress FFmpeg logs
            "-i", input_file,  # Input file
            "-c:a", "aac_mf",  # Use AAC (acc_mf is hardware accelerated on windows)
            "-b:a", "64k",  # Set bitrate to 32kbps
        ]

        for flag, value in kwargs.items():
            command.append(str(flag))
            command.append(str(value))

        # Append the output file to the command
        command.append(output_file)

        # Run the FFmpeg command asynchronously
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(f"FFmpeg error: {stderr.decode()}")

    except FileNotFoundError:
        logging.error("FFmpeg is not installed or not found in the system PATH.")
        raise FileNotFoundError("FFmpeg is not installed or not found in the system PATH.")
    except Exception as ex:
        logging.error(f"An unexpected error occurred: {ex}")
        raise ex


async def compress_and_replace(file_codec: str, compressed_codec: str, directory: str, input_file, **kwargs) -> int:
    """
    Compress the input file, save it to a temporary file, and replace the original file with the compressed version.

    :returns: the size (in bytes) of the compressed file
    """

    temp_file = os.path.join(directory, f"temp_{input_file}.{compressed_codec}")
    full_input_path = os.path.join(directory, f"{input_file}.{file_codec}")

    try:
        # Compress the file
        await compress_audio(full_input_path, temp_file, **kwargs)

        # despite path.exists() NOT being async, it shouldn't matter all that much because it isn't very resource-intensive
        if os.path.exists(full_input_path):
            # async deletes the original file, as it isn't needed anymore
            await aos.remove(full_input_path)

        new_file = os.path.join(directory, f"{input_file}.{compressed_codec}")

        # async rename temporary file
        await aos.rename(temp_file, new_file)

        file_info = await aos.stat(new_file)
        new_file_size = file_info.st_size

        return new_file_size
    except Exception as e:
        if os.path.exists(temp_file):
            os.remove(temp_file)  # Clean up temp file in case of failure

        raise e
