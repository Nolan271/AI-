"""使用火山引擎 TTS 生成视频旁白音频，并用 ffprobe 测量实际时长进行校准"""

import asyncio
import json
import subprocess
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.tts_service import VolcTTSService


def get_audio_duration(audio_path: Path) -> float:
    """Use ffprobe to get the exact duration of an audio file in seconds."""
    ffprobe = str(audio_path.parent.parent.parent / "ffmpeg-bin" / "ffprobe.exe")
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
        capture_output=True, text=True,
    )
    return float(result.stdout.strip())


async def main():
    # 读取脚本
    script_path = Path(__file__).parent / "video_script.json"
    script = json.loads(script_path.read_text(encoding="utf-8"))

    # 拼接所有旁白文本
    all_narration = ""
    for scene in script["scenes"]:
        all_narration += scene["narration_text"] + " "

    all_narration = all_narration.strip()
    print(f"旁白总字数: {len(all_narration)}")
    print(f"旁白内容: {all_narration[:100]}...")

    # 生成 TTS
    tts = VolcTTSService()
    output_dir = Path(__file__).parent.parent / "output" / "audio"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "orientation_narration.mp3"

    print(f"正在生成 TTS 音频...")
    result = await tts.synthesize(all_narration, output_path)
    file_size = result.stat().st_size
    print(f"TTS 音频生成完成: {result}")
    print(f"   文件大小: {file_size / 1024:.1f} KB")

    # 用 ffprobe 测量实际时长
    actual_total = get_audio_duration(result)
    print(f"   实际时长: {actual_total:.1f}s")

    # 按各场景文本字数比例分配实际时长
    scenes = script["scenes"]
    total_chars = sum(len(s["narration_text"]) for s in scenes)
    current_time = 0.0
    scene_timings = []
    for scene in scenes:
        ratio = len(scene["narration_text"]) / total_chars
        dur = round(actual_total * ratio, 1)
        end = round(current_time + dur, 1)
        scene_timings.append({
            "index": scene["index"],
            "title": scene["title"],
            "start_time": round(current_time, 1),
            "duration": dur,
            "end_time": end,
            "narration_text": scene["narration_text"],
            "visual_description": scene["visual_description"],
        })
        print(f"  场景 {scene['index']} ({scene['title']}): {dur}s (start={current_time:.1f}, end={end})")
        current_time = end

    print(f"\n实际总时长: {current_time:.1f}s")

    # 保存时间信息
    timing_path = script_path.parent / "scene_timings.json"
    timing_path.write_text(
        json.dumps(scene_timings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"时间信息保存至: {timing_path}")


if __name__ == "__main__":
    asyncio.run(main())
