"""Volcengine (火山引擎/豆包) TTS speech synthesis service.

Uses the Volcengine Speech API V3 WebSocket bidirectional protocol
(豆包语音合成大模型2.0, seed-tts-2.0) to generate
natural-sounding Chinese narration audio from text.

API doc: https://www.volcengine.com/docs/6561/1329505
New console auth: X-Api-Key (simplified, no appid/token needed)
"""

import asyncio
import json
import struct
import uuid
from pathlib import Path
from typing import Optional

import websockets

from app.config import settings


# =========================================================================
# Event codes for the V3 bidirectional protocol (see API doc §2.3)
# =========================================================================
class _Event:
    """WebSocket binary protocol event codes."""
    START_CONNECTION = 1
    FINISH_CONNECTION = 2
    CONNECTION_STARTED = 50
    CONNECTION_FAILED = 51
    CONNECTION_FINISHED = 52
    START_SESSION = 100
    CANCEL_SESSION = 101
    FINISH_SESSION = 102
    SESSION_STARTED = 150
    SESSION_CANCELED = 151
    SESSION_FINISHED = 152
    SESSION_FAILED = 153
    TASK_REQUEST = 200
    TTS_SENTENCE_START = 350
    TTS_SENTENCE_END = 351
    TTS_RESPONSE = 352


# Default API endpoint
_DEFAULT_API_ENDPOINT = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
_DEFAULT_RESOURCE_ID = "seed-tts-2.0"


# =========================================================================
# Voice types for 豆包语音合成大模型2.0 (seed-tts-2.0)
# =========================================================================
VOLC_VOICES = {
    "Vivi 2.0": "zh_female_vv_uranus_bigtts",
    "TVB女声 2.0": "zh_female_tvbnv_uranus_bigtts",
    "甜美桃子 2.0": "zh_female_tianmeitaozi_mars_bigtts",
    "爽朗少年 2.0": "zh_female_shuangkuaisisi_moon_bigtts",
    "译制片男 2.0": "zh_male_yizhipiannan_uranus_bigtts",
}


class VolcTTSError(Exception):
    """Volcengine TTS API exception."""
    pass


# =========================================================================
# Binary frame helpers (see API doc §2.1 - WebSocket 二进制协议)
# =========================================================================

def _build_binary_frame(
    event: int,
    payload: dict,
    session_id: Optional[str] = None,
) -> bytes:
    """Build a binary frame for the V3 WebSocket protocol.

    Frame format (API doc §2.1):
      Byte 0:  [protocol_version(4) | header_size(4)]
      Byte 1:  [message_type(4) | specific_flags(4)]
      Byte 2:  [serialization(4) | compression(4)]
      Byte 3:  reserved
      Bytes 4-7:    event number (int32 big-endian)
      [session_id_len(4) + session_id]  (if session_id provided)
      payload_len(4) + payload (JSON bytes)
    """
    payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    frame = bytearray()
    frame.append(0b0001_0001)   # v1 | 4-byte header
    frame.append(0b0001_0100)   # Full-client request | has event number
    frame.append(0b0001_0000)   # JSON | no compression
    frame.append(0b0000_0000)   # reserved
    frame.extend(struct.pack(">i", event))  # event code (int32 big-endian)

    if session_id is not None:
        sid_bytes = session_id.encode("utf-8")
        frame.extend(struct.pack(">I", len(sid_bytes)))
        frame.extend(sid_bytes)

    frame.extend(struct.pack(">I", len(payload_bytes)))
    frame.extend(payload_bytes)

    return bytes(frame)


def _build_empty_frame(event: int, session_id: Optional[str] = None) -> bytes:
    """Build a binary frame with empty JSON payload ``{}``."""
    return _build_binary_frame(event, {}, session_id)


def _build_start_session_frame(
    session_id: str,
    speaker: str,
    audio_format: str = "mp3",
    sample_rate: int = 24000,
) -> bytes:
    """Build a StartSession frame with TTS parameters.

    See API doc §2.1 Payload request parameters.
    """
    payload = {
        "event": _Event.START_SESSION,
        "req_params": {
            "speaker": speaker,
            "audio_params": {
                "format": audio_format,
                "sample_rate": sample_rate,
            },
        },
    }
    return _build_binary_frame(_Event.START_SESSION, payload, session_id)


def _build_task_request_frame(session_id: str, text: str) -> bytes:
    """Build a TaskRequest frame with the text to synthesize."""
    payload = {
        "event": _Event.TASK_REQUEST,
        "req_params": {
            "text": text,
        },
    }
    return _build_binary_frame(_Event.TASK_REQUEST, payload, session_id)


def _parse_frame(data: bytes) -> dict:
    """Parse a binary response frame from the server."""
    if not isinstance(data, bytes):
        raise ValueError(f"Expected bytes, got {type(data)}")
    if len(data) < 8:
        raise ValueError(f"Frame too short: {len(data)} bytes")

    header = data[:4]
    header_size = (header[0] & 0x0F) * 4
    message_type = header[1] >> 4
    flags = header[1] & 0x0F

    offset = header_size   # skip base header

    # Parse event number (present when flags & 0x04)
    if flags & 0x04:
        event = struct.unpack(">i", data[offset:offset + 4])[0]
        offset += 4
    else:
        event = None

    # Parse session_id (present for Full-client/server and Audio-only messages)
    session_id: Optional[str] = None
    if message_type in (0b0001, 0b1001, 0b1011) and offset + 4 <= len(data):
        sid_len = struct.unpack(">I", data[offset:offset + 4])[0]
        offset += 4
        if offset + sid_len <= len(data):
            session_id = data[offset:offset + sid_len].decode("utf-8", errors="replace")
            offset += sid_len

    # Parse payload
    payload = b""
    if offset + 4 <= len(data):
        payload_len = struct.unpack(">I", data[offset:offset + 4])[0]
        offset += 4
        if offset + payload_len <= len(data):
            payload = data[offset:offset + payload_len]

    return {
        "event": event,
        "session_id": session_id,
        "payload": payload,
        "message_type": message_type,
    }


# =========================================================================
# Main TTS Service
# =========================================================================

class VolcTTSService:
    """Volcengine Text-to-Speech service using V3 WebSocket bidirectional protocol.

    Authentication uses the new console style (X-Api-Key) — see API doc §2.1.1.
    Resource ID defaults to ``seed-tts-2.0`` (豆包语音合成大模型2.0).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        resource_id: str = _DEFAULT_RESOURCE_ID,
        voice_type: str = "zh_female_vv_uranus_bigtts",
        sample_rate: int = 24000,
        audio_format: str = "mp3",
        api_url: str = _DEFAULT_API_ENDPOINT,
    ):
        self.api_key = api_key or settings.volc_tts_api_key
        self.resource_id = resource_id
        self.voice_type = voice_type
        self.sample_rate = sample_rate
        self.audio_format = audio_format
        self.api_url = api_url

        if not self.api_key:
            raise VolcTTSError(
                "Volcengine TTS API key is required. Set VOLC_TTS_API_KEY in .env"
            )

    # ------------------------------------------------------------------
    # Context manager for a full TTS WebSocket session
    # ------------------------------------------------------------------

    async def _run_session(self, text: str) -> bytes:
        """Execute a complete TTS session: connect → synthesize → disconnect.

        Protocol flow (API doc §2.3 + TTS2.0 interaction diagram):
          1. StartConnection  →  ConnectionStarted
          2. StartSession     →  SessionStarted
          3. TaskRequest (text)
          4. FinishSession
          5. TTS_RESPONSE × N  |  TTSSentenceStart/End  |  SessionFinished
          6. FinishConnection →  ConnectionFinished
        """
        if not text.strip():
            raise VolcTTSError("Cannot synthesize empty text")

        session_id = str(uuid.uuid4())
        audio_chunks: list[bytes] = []
        finish_sent = False

        headers = {
            "X-Api-Key": self.api_key,
            "X-Api-Resource-Id": self.resource_id,
        }

        async with websockets.connect(
            self.api_url,
            additional_headers=headers,
            max_size=2**31,  # allow large audio payloads (2GB)
        ) as ws:
            # ── 1. StartConnection ──────────────────────────────────
            await ws.send(_build_empty_frame(_Event.START_CONNECTION))
            resp = await ws.recv()
            parsed = _parse_frame(resp)
            if parsed["event"] == _Event.CONNECTION_FAILED:
                raise VolcTTSError(
                    f"Connection failed: {parsed['payload'].decode('utf-8', errors='replace')}"
                )

            # ── 2. StartSession ─────────────────────────────────────
            await ws.send(_build_start_session_frame(
                session_id, self.voice_type, self.audio_format, self.sample_rate,
            ))
            resp = await ws.recv()
            parsed = _parse_frame(resp)
            if parsed["event"] != _Event.SESSION_STARTED:
                raise VolcTTSError(
                    f"Session failed to start: "
                    f"{parsed['payload'].decode('utf-8', errors='replace')}"
                )

            # ── 3. TaskRequest (send all text) ──────────────────────
            await ws.send(_build_task_request_frame(session_id, text))

            # ── 4. FinishSession (tell server we're done sending) ───
            await ws.send(_build_empty_frame(_Event.FINISH_SESSION, session_id))
            finish_sent = True

            # ── 5. Receive audio + events until session ends ────────
            while True:
                resp = await ws.recv()
                parsed = _parse_frame(resp)

                if parsed["event"] == _Event.TTS_RESPONSE:
                    audio_chunks.append(parsed["payload"])
                elif parsed["event"] in (_Event.SESSION_FINISHED, _Event.CONNECTION_FINISHED):
                    break
                elif parsed["event"] == _Event.SESSION_FAILED:
                    err = parsed["payload"].decode("utf-8", errors="replace")
                    raise VolcTTSError(f"Session failed: {err}")
                # TTSSentenceStart / TTSSentenceEnd — informational, skip

            # ── 6. FinishConnection (cleanup) ───────────────────────
            if not finish_sent:
                await ws.send(_build_empty_frame(_Event.FINISH_CONNECTION))

        return b"".join(audio_chunks)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def synthesize(self, text: str, output_path: Path) -> Path:
        """Synthesize *text* to speech and save to *output_path* (MP3).

        Returns the absolute path of the saved audio file.
        """
        audio_data = await self._run_session(text)

        if not audio_data or len(audio_data) < 100:
            raise VolcTTSError(
                f"TTS response too small ({len(audio_data)} bytes) — "
                f"possible synthesis error"
            )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(audio_data)

        return output_path

    async def synthesize_and_return_bytes(self, text: str) -> bytes:
        """Synthesize *text* and return raw audio bytes without saving."""
        return await self._run_session(text)


# Singleton convenience instance
tts_service = VolcTTSService()
