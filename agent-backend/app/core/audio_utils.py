"""Audio utilities: duration measurement via ffprobe and composition via ffmpeg."""

import asyncio
import json
import subprocess
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
    proc = await _run_process(cmd)
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {_decode_output(proc.stderr)}")
    info = json.loads(_decode_output(proc.stdout))
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
    proc = await _run_process(cmd)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg composition failed: {_decode_output(proc.stderr)}")
    return output_path


async def _run_process(cmd: list[str]) -> subprocess.CompletedProcess[bytes]:
    """Run a CLI command without relying on Windows asyncio subprocess support."""
    return await asyncio.to_thread(
        subprocess.run,
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _decode_output(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")
