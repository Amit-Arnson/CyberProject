import os
import asyncio

import aiofiles.os as aos

import logging


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
            "-c:a", "libopus",  # Use Opus codec
            "-b:a", "32k",  # Set bitrate to 32kbps
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

        print(f"Conversion successful! Output saved as: {output_file}")
    except FileNotFoundError:
        logging.error("FFmpeg is not installed or not found in the system PATH.")
    except Exception as ex:
        logging.error(f"An unexpected error occurred: {ex}")


async def compress_and_replace(file_extension: str, compressed_extension: str, directory: str, input_file, **kwargs):
    """
    Compress the input file, save it to a temporary file, and replace the original file with the compressed version.
    """

    temp_file = os.path.join(directory, f"temp_{input_file}.{compressed_extension}")
    full_input_path = os.path.join(directory, f"{input_file}.{file_extension}")

    try:
        # Compress the file
        await compress_audio(full_input_path, temp_file, **kwargs)

        # despite path.exists() NOT being async, it shouldn't matter all that much because it isn't very resource-intensive
        if os.path.exists(full_input_path):
            # async deletes the original file, as it isn't needed anymore
            await aos.remove(full_input_path)

        new_file = os.path.join(directory, f"{input_file}.{compressed_extension}")

        # async rename temporary file
        await aos.rename(temp_file, new_file)
    except Exception as e:
        if os.path.exists(temp_file):
            os.remove(temp_file)  # Clean up temp file in case of failure

        raise e
