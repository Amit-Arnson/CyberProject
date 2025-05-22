import asyncio
import numpy as np
import librosa
import io


async def decode_audio_bytes(audio_bytes: bytes) -> tuple[np.ndarray, int]:
    ffmpeg_exe = r".\ffmpeg\bin\ffmpeg.exe"

    process = await asyncio.create_subprocess_exec(
        ffmpeg_exe,
        "-loglevel", "quiet",
        "-i", "pipe:0",               # Input from stdin
        "-f", "wav",                  # Output as WAV (librosa can read this)
        "-ac", "1",                   # Mono
        "-ar", "22050",               # Resample to a standard rate
        "pipe:1",                     # Output to stdout
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate(input=audio_bytes)

    if process.returncode != 0:
        raise Exception(f"FFmpeg failed: {stderr.decode()}")

    # Load audio with librosa directly from stdout bytes
    audio_buffer = io.BytesIO(stdout)
    y, sr = librosa.load(audio_buffer, sr=None, mono=True)  # Keep native sample rate or set one
    return y, sr
