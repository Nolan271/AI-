"""HeyGen API 数字人口播视频生成服务"""

import time
import json
import requests
from pathlib import Path
from typing import Optional

from app.config import settings


# 常用 HeyGen 女性数字人 ID
DEFAULT_FEMALE_AVATARS = {
    "Anna": "Anna_public_3_20240119",       # 专业女性
    "Olivia": "Olivia_public_3_20240119",    # 亲和女性
    "Mia": "Mia_public_3_20240119",          # 知性女性
    "Sara": "Sara_public_3_20240119",        # 干练女性
}

# 常用中文语音 ID（HeyGen 标准语音）
DEFAULT_CHINESE_VOICES = {
    "xiaobei": "2d9d16b7e4d146e89819c80f6ff47753",   # 小北 - 标准女声
    "yunjian": "8bc0a469f2ee42b38e6c16aa57e8e5f3",    # 云健 - 标准男声
    "annie": "5b1d4d0e8fdc4f8e8e8e8e8e8e8e8e8e",      # Annie - 英文女声
}


class HeyGenAvatarError(Exception):
    """HeyGen API 异常"""
    pass


class AvatarService:
    """HeyGen 数字人口播视频生成服务"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        avatar_id: str = "Anna_public_3_20240119",
        voice_id: str = "2d9d16b7e4d146e89819c80f6ff47753",
    ):
        self.api_key = api_key or settings.heygen_api_key
        self.avatar_id = avatar_id
        self.voice_id = voice_id
        self.base_url = "https://api.heygen.com"

        if not self.api_key:
            raise HeyGenAvatarError(
                "HeyGen API key is required. Set HEYGEN_API_KEY in .env"
            )

    def _headers(self) -> dict:
        return {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def generate_video(
        self,
        input_text: str,
        title: str = "Avatar Video",
        avatar_style: str = "normal",
        background_color: str = "#00000000",  # 透明背景
        video_aspect_ratio: str = "9:16",
        voice_speed: float = 1.0,
    ) -> str:
        """生成数字人口播视频，返回 video_id"""
        url = f"{self.base_url}/v2/video/generate"

        payload = {
            "video_aspect_ratio": video_aspect_ratio,
            "title": title,
            "avatar": {
                "avatar_id": self.avatar_id,
                "avatar_style": avatar_style,
                "scale": 1.0,
                "offset": {"x": 0, "y": 0},
            },
            "voice": {
                "voice_id": self.voice_id,
                "input_text": input_text,
                "speed": voice_speed,
            },
            "background": {
                "type": "color",
                "value": background_color,
            },
        }

        resp = requests.post(url, headers=self._headers(), json=payload)
        data = resp.json()

        if resp.status_code != 200 or data.get("code") != 100:
            raise HeyGenAvatarError(
                f"Failed to generate video: {data.get('message', resp.text)}"
            )

        return data["data"]["video_id"]

    def poll_video_status(
        self,
        video_id: str,
        timeout: int = 600,
        interval: int = 5,
    ) -> dict:
        """轮询视频生成状态，直到完成或超时"""
        url = f"{self.base_url}/v1/video_status.get"
        params = {"video_id": video_id}

        start = time.time()
        while time.time() - start < timeout:
            resp = requests.get(url, headers=self._headers(), params=params)
            data = resp.json()

            if resp.status_code != 200:
                raise HeyGenAvatarError(
                    f"Status check failed: {data.get('message', resp.text)}"
                )

            status = data["data"]["status"]
            if status == "completed":
                return data["data"]
            elif status == "failed":
                raise HeyGenAvatarError(
                    f"Video generation failed: {data['data'].get('error', 'Unknown error')}"
                )

            time.sleep(interval)

        raise HeyGenAvatarError(f"Video generation timed out after {timeout}s")

    def generate_and_download(
        self,
        input_text: str,
        output_path: Path,
        title: str = "Avatar Video",
        **kwargs,
    ) -> Path:
        """完整流程：生成视频 → 等待完成 → 下载到本地"""
        # Step 1: 创建视频生成任务
        video_id = self.generate_video(
            input_text=input_text,
            title=title,
            **kwargs,
        )
        print(f"[Avatar] 视频生成任务已创建，video_id: {video_id}")

        # Step 2: 轮询等待完成
        result = self.poll_video_status(video_id)
        video_url = result.get("video_url", "")
        if not video_url:
            raise HeyGenAvatarError("No video_url in completed response")

        print(f"[Avatar] 视频生成完成，正在下载...")

        # Step 3: 下载视频
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        video_resp = requests.get(video_url, stream=True)
        with open(str(output_path), "wb") as f:
            for chunk in video_resp.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"[Avatar] 视频已保存到: {output_path}")
        return output_path


def get_avatar_options() -> dict:
    """获取可用的数字人选项（供前端展示）"""
    return {
        "female": [
            {"id": "Anna_public_3_20240119", "name": "Anna - 专业女性"},
            {"id": "Olivia_public_3_20240119", "name": "Olivia - 亲和女性"},
            {"id": "Mia_public_3_20240119", "name": "Mia - 知性女性"},
            {"id": "Sara_public_3_20240119", "name": "Sara - 干练女性"},
        ],
        "voices": [
            {"id": "2d9d16b7e4d146e89819c80f6ff47753", "name": "小北 - 标准中文女声"},
        ],
    }
