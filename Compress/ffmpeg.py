import os
import logging

import asyncio
from enum import Enum


class Codec(Enum):
    AAC = "aac"  # Advanced Audio Codec
    AAC_MF = "aac_mf"  # hardware-accelerated AAC (on windows)
    FLAC = "flac"  # Free Lossless Audio Codec
    MP3 = "mp3"  # MPEG Audio Layer III
    OPUS = "libopus"  # Opus Audio Codec
    VORBIS = "libvorbis"  # Vorbis Codec
    WAV = "pcm_s16le"  # Uncompressed PCM Audio

    JPEG = "mjpeg"  # Motion JPEG
    PNG = "png"  # Portable Network Graphics
    GIF = "gif"  # Graphics Interchange Format
    WEBP = "libwebp"  # WebP Codec
    TIFF = "tiff"  # Tagged Image File Format
    AVIF = "libaom-av1"  # AV1 Image File Format


class FFmpegAudio:
    def __init__(self, codec: str | Codec = None, bitrate: str = None, channels: int = None, sample_rate: int = None):
        self.codec = codec
        if isinstance(codec, Codec):
            self.codec = self.codec.value

        self.bitrate = bitrate  # e.g., "128k"
        self.channels = channels  # e.g., 2
        self.sample_rate = sample_rate  # e.g., 44100

    def to_dict(self, extra: dict[str, str] = None) -> dict[str, str]:
        flags = {}
        if self.codec:
            flags["-c:a"] = self.codec
        if self.bitrate:
            flags["-b:a"] = self.bitrate
        if self.channels:
            flags["-ac"] = str(self.channels)
        if self.sample_rate:
            flags["-ar"] = str(self.sample_rate)

        if extra:
            flags.update(extra)

        return flags


class FFmpegImage:
    def __init__(self, codec: str | Codec = None, resolution: str = None, frame_rate: int = None, quality: int = None):
        self.codec = codec
        if isinstance(codec, Codec):
            self.codec = self.codec.value

        self.resolution = resolution  # e.g., "1920x1080"
        self.frame_rate = frame_rate  # e.g., 30
        self.quality = quality  # e.g., 23

    def to_dict(self, extra: dict[str, ...] = None) -> dict[str, str]:
        flags = {}
        if self.codec:
            flags["-c:v"] = self.codec
        if self.resolution:
            flags["-s"] = self.resolution
        if self.frame_rate:
            flags["-r"] = str(self.frame_rate)
        if self.quality is not None:  # Quality is typically for codecs like libx264
            flags["-q:v"] = str(self.quality)

        if extra:
            extra = self._to_string(extra)
            flags.update(extra)

        return flags

    @staticmethod
    def _to_string(flags: dict[str, ...]) -> dict[str, str]:
        to_string_flags: dict[str, str] = {
            flag: str(value) for flag, value in flags.items()
        }

        return to_string_flags


async def is_valid_file(file_path: str) -> bool:
    """
    Validates a file's integrity. If the file is corrupted or uses false data, this function will return False, else True
    """

    ffprobe_exe = r".\ffmpeg\bin\ffprobe.exe"  # Update this to the correct path

    try:
        # Build the ffprobe command
        command = [
            ffprobe_exe,
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
        logging.error("ffprobe executable not found. Make sure it's in the specified path.")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return False


async def compress(input_file: str, output_file: str, flag_values: dict[str, str]) -> None:
    """
    Compresses the input file using the flags given.
    note: no need to add the "-i" flag, as it is set automatically
    """

    # Ensure FFmpeg is in the system PATH
    ffmpeg_exe = r".\ffmpeg\bin\ffmpeg.exe"

    if not os.path.exists(ffmpeg_exe):
        raise Exception(f"Couldn't find the FFmpeg executable in {ffmpeg_exe}")

    try:
        # Command to convert the audio file using FFmpeg
        command = [
            ffmpeg_exe,
            "-loglevel", "quiet",  # Suppress FFmpeg logs
            "-i", input_file,  # Input file
        ]

        for flag, value in flag_values.items():
            command.append(flag)
            command.append(value)

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

