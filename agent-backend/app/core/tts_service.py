"""Volcengine (火山引擎/豆包) TTS speech synthesis service.

Uses the Volcengine Speech API (V3, 豆包语音合成大模型) to generate
natural-sounding Chinese narration audio from text.
"""

import json
import uuid
from pathlib import Path
from typing import Optional

import httpx
from app.config import settings


# Default Chinese female voice IDs for Volcengine TTS
VOLC_VOICES = {
    "zh_female_standard": "BV001_streaming",    # 标准女声
    "zh_female_sweet": "BV056_streaming",        # 甜美女声
    "zh_female_warm": "BV064_streaming",         # 温暖女声
    "zh_male_standard": "BV002_streaming",       # 标准男声
}


class VolcTTSError(Exception):
    """Volcengine TTS API exception"""
    pass


class VolcTTSService:
    """Volcengine Text-to-Speech service using the Speech API V3."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_type: str = "BV056_streaming",
        speed_ratio: float = 1.0,
        volume_ratio: float = 1.0,
        pitch_ratio: float = 1.0,
        api_url: str = "https://openspeech.bytedance.com/api/v1/tts",
    ):
        self.api_key = api_key or settings.volc_tts_api_key
        self.voice_type = voice_type or settings.volc_tts_voice_type
        self.speed_ratio = speed_ratio
        self.volume_ratio = volume_ratio
        self.pitch_ratio = pitch_ratio
        self.api_url = api_url

        if not self.api_key:
            raise VolcTTSError(
                "Volcengine TTS API key is required. Set VOLC_TTS_API_KEY in .env"
            )

    def _build_payload(self, text: str) -> dict:
        """Build the request payload for the Volcengine TTS V3 API."""
        return {
            "app": {
                "appid": "",
                "token": self.api_key,
                "cluster": "volcano_tts",
            },
            "user": {
                "uid": "video-agent-user",
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": text,
                "text_type": "plain",
                "operation": "query",
                "voice_type": self.voice_type,
                "speed_ratio": self.speed_ratio,
                "volume_ratio": self.volume_ratio,
                "pitch_ratio": self.pitch_ratio,
            },
        }

    async def synthesize(
        self,
        text: str,
        output_path: Path,
    ) -> Path:
        """Synthesize text to speech and save to the given path.

        Returns:
            Path to the saved audio file (MP3 format).
        """
        if not text.strip():
            raise VolcTTSError("Cannot synthesize empty text")

        payload = self._build_payload(text)
        headers = {
            "Authorization": f"Bearer;{self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.api_url,
                headers=headers,
                json=payload,
            )

        if response.status_code != 200:
            raise VolcTTSError(
                f"TTS request failed (status {response.status_code}): "
                f"{response.text[:500]}"
            )

        # The V3 API returns audio data directly in the response body (MP3 format)
        audio_data = response.content

        if len(audio_data) < 100:
            # Might be an error JSON response
            try:
                err = json.loads(audio_data)
                raise VolcTTSError(
                    f"TTS API error: {err.get('message', response.text[:300])}"
                )
            except json.JSONDecodeError:
                raise VolcTTSError(
                    f"TTS response too small ({len(audio_data)} bytes): {response.text[:200]}"
                )

        # Save audio file
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(audio_data)

        return output_path

    async def synthesize_and_return_bytes(self, text: str) -> bytes:
        """Synthesize text to speech and return audio bytes without saving."""
        if not text.strip():
            raise VolcTTSError("Cannot synthesize empty text")

        payload = self._build_payload(text)
        headers = {
            "Authorization": f"Bearer;{self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.api_url,
                headers=headers,
                json=payload,
            )

        if response.status_code != 200:
            raise VolcTTSError(
                f"TTS request failed (status {response.status_code}): "
                f"{response.text[:500]}"
            )

        return response.content


# Singleton instance
tts_service = VolcTTSService()
