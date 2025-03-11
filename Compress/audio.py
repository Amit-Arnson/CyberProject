import os
import subprocess

import logging


# todo: make this async friendly
async def compress_audio(input_file: str, output_file: str, **kwargs):
    """
    Compresses the input audio file to the specified output file using FFmpeg asynchronously.
    """

    # Ensure FFmpeg is in the system PATH
    ffmpeg_cmd = r".\ffmpeg\bin\ffmpeg.exe"

    if not os.path.exists(ffmpeg_cmd):
        raise Exception(f"couldn't find the ffmpeg executable in {ffmpeg_cmd}")

    try:
        # Command to convert the audio file using FFmpeg
        command = [
            ffmpeg_cmd,
            "-loglevel", "quiet",  # Suppress FFmpeg logs
            "-i", input_file,  # Input file
            "-c:a", "libopus",
            "-b:a", "32k",
        ]

        for flag, value in kwargs.items():
            command.append(str(flag))
            command.append(str(value))

        # to make sure it is the last thing in the command
        command.append(output_file)

        # Run the FFmpeg command
        subprocess.run(command, check=True)
        print(f"Conversion successful! Output saved as: {output_file}")
    except FileNotFoundError:
        logging.error("FFmpeg is not installed or not found in the system PATH.")
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg encountered an error: {e}")
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

        # Replace the original file
        if os.path.exists(full_input_path):
            os.remove(full_input_path)  # Delete original file

        true_file = os.path.join(directory, f"{input_file}.{compressed_extension}")

        os.rename(temp_file, true_file)  # Rename temporary file
    except Exception as e:
        raise e