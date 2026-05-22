"""Audio utilities: duration measurement via ffprobe and composition via ffmpeg."""

import asyncio
import json
from pathlib import Path

FFPROBE_PATH = r"D:\Users\muzhi\Desktop\hhDome\ffmpeg-bin\ffprobe.exe"
FFMPEG_PATH = r"D:\Users\muzhi\Desktop\hhDome\ffmpeg-bin\ffmpeg.exe"


async def get_audio_duration(audio_path: Path) -> float:
    """Get audio duration in seconds using ffprobe."""
    cmd = [
        str(FFPROBE_PATH),
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        str(audio_path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {stderr.decode()}")
    info = json.loads(stdout.decode())
    return float(info["format"]["duration"])


async def compose_audio_video(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
) -> Path:
    """Compose audio and rendered video into final MP4.

    Uses -shortest to trim the video to match audio duration.
    """
    cmd = [
        str(FFMPEG_PATH),
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        "-y",
        str(output_path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg composition failed: {stderr.decode()}")
    return output_path
