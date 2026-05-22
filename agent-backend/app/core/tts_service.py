"""Volcengine (火山引擎/豆包) TTS speech synthesis service.

Uses the Volcengine Speech API V3 WebSocket bidirectional protocol
(豆包语音合成大模型2.0, seed-tts-2.0) to generate
natural-sounding Chinese narration audio from text.

API doc: https://www.volcengine.com/docs/6561/1329505
New console auth: X-Api-Key (simplified, no appid/token needed)
"""

import asyncio
import base64
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


# Message types (upper nibble of byte 1 in binary frame)
_MSG_FULL_CLIENT_REQUEST = 0b0001     # client → server
_MSG_FULL_SERVER_RESPONSE = 0b1001    # server → client (JSON payload)
_MSG_AUDIO_ONLY_RESPONSE = 0b1011     # server → client (raw audio data)
_MSG_ERROR = 0b1111

# Flag bits for byte 1 lower nibble
_FLAG_HAS_EVENT = 0b0100               # optional section contains event number

# Default API endpoint
_DEFAULT_API_ENDPOINT = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"


# =========================================================================
# Voice types for 豆包语音合成大模型2.0 (seed-tts-2.0)
# =========================================================================
VOLC_VOICES = {
    # 通用场景
    "Vivi 2.0 — 专业活力": "zh_female_vv_uranus_bigtts",
    # 视频配音
    "大壹 — 沉稳解说": "zh_male_dayi_saturn_bigtts",
    "咪仔 — 灵动叙事": "zh_female_mizai_saturn_bigtts",
    "鸡汤女 — 温柔知性": "zh_female_jitangnv_saturn_bigtts",
    "魅力女友 — 甜美亲和": "zh_female_meilinvyou_saturn_bigtts",
    "流畅女声 — 清晰流畅": "zh_female_santongyongns_saturn_bigtts",
    "儒雅逸辰 — 温润儒雅": "zh_male_ruyayichen_saturn_bigtts",
    # 有声阅读
    "儿童绘本 — 活泼童趣": "zh_female_xueayi_saturn_bigtts",
    # 趣味口音
    "粤语小溏 — 粤语女声": "zh_female_yueyunv_mars_bigtts",
    # 多情感
    "深夜播客 — 磁性深沉": "zh_male_shenyeboke_emo_v2_mars_bigtts",
    # 角色扮演
    "清朗温润 — 温润公子": "ICL_zh_male_renyuwangzi_v1_tob",
    "清冷矜贵 — 清冷贵气": "ICL_zh_male_liyisheng_v1_tob",
    "甜美娇俏 — 甜美少女": "ICL_zh_female_linxueying_v1_tob",
    "成熟温柔 — 成熟御姐": "ICL_zh_female_chengshu_v1_tob",
    "高冷沉稳 — 高冷男声": "zh_male_bv139_audiobook_ummv3_bigtts",
}

VOICE_CATEGORIES = {
    "通用场景": [
        "Vivi 2.0 — 专业活力",
    ],
    "视频配音": [
        "大壹 — 沉稳解说",
        "咪仔 — 灵动叙事",
        "鸡汤女 — 温柔知性",
        "魅力女友 — 甜美亲和",
        "流畅女声 — 清晰流畅",
        "儒雅逸辰 — 温润儒雅",
    ],
    "有声阅读": [
        "儿童绘本 — 活泼童趣",
    ],
    "趣味口音": [
        "粤语小溏 — 粤语女声",
    ],
    "多情感": [
        "深夜播客 — 磁性深沉",
    ],
    "角色扮演": [
        "清朗温润 — 温润公子",
        "清冷矜贵 — 清冷贵气",
        "甜美娇俏 — 甜美少女",
        "成熟温柔 — 成熟御姐",
        "高冷沉稳 — 高冷男声",
    ],
}


class VolcTTSError(Exception):
    """Volcengine TTS API exception."""
    pass


# =========================================================================
# Binary frame helpers (see API doc §2.1 - WebSocket 二进制协议)
# =========================================================================

def _build_header(message_type: int = _MSG_FULL_CLIENT_REQUEST,
                  flags: int = _FLAG_HAS_EVENT) -> bytes:
    """Build the 4-byte binary protocol header."""
    b0 = (0b0001 << 4) | 0b0001
    b1 = (message_type << 4) | flags
    b2 = (0b0001 << 4) | 0b0000
    b3 = 0b0000
    return bytes([b0, b1, b2, b3])


def _build_optional(event: int, session_id: Optional[str] = None) -> bytes:
    """Build the optional section: event(4) + [session_id_len(4) + session_id]."""
    opt = bytearray()
    opt.extend(struct.pack(">i", event))
    if session_id is not None:
        sid_bytes = session_id.encode("utf-8")
        opt.extend(struct.pack(">I", len(sid_bytes)))
        opt.extend(sid_bytes)
    return bytes(opt)


def _build_v3_payload(event: int, text: str = "", speaker: str = "",
                      audio_format: str = "mp3",
                      sample_rate: int = 24000,
                      user_uid: str = "user") -> dict:
    """Build a V3 bidirectional protocol JSON payload.

    V3 requires ``namespace: "BidirectionalTTS"`` and ``user.uid``
    in every payload (unlike the older V2 format).
    """
    return {
        "user": {"uid": user_uid},
        "event": event,
        "namespace": "BidirectionalTTS",
        "req_params": {
            "text": text,
            "speaker": speaker,
            "audio_params": {
                "format": audio_format,
                "sample_rate": sample_rate,
            },
        },
    }


def _build_binary_frame(
    event: int,
    payload: dict,
    session_id: Optional[str] = None,
) -> bytes:
    """Build a complete binary frame for the V3 WebSocket protocol."""
    payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    header = _build_header(_MSG_FULL_CLIENT_REQUEST, _FLAG_HAS_EVENT)
    optional = _build_optional(event, session_id)

    frame = bytearray()
    frame.extend(header)
    frame.extend(optional)
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
    user_uid: str = "user",
) -> bytes:
    """Build a StartSession frame (V3 protocol format with namespace)."""
    payload = _build_v3_payload(
        event=_Event.START_SESSION,
        text="",
        speaker=speaker,
        audio_format=audio_format,
        sample_rate=sample_rate,
        user_uid=user_uid,
    )
    return _build_binary_frame(_Event.START_SESSION, payload, session_id)


def _build_task_request_frame(
    session_id: str,
    text: str,
    speaker: str,
    audio_format: str = "mp3",
    sample_rate: int = 24000,
    user_uid: str = "user",
) -> bytes:
    """Build a TaskRequest frame with full parameters (V3 format)."""
    payload = _build_v3_payload(
        event=_Event.TASK_REQUEST,
        text=text,
        speaker=speaker,
        audio_format=audio_format,
        sample_rate=sample_rate,
        user_uid=user_uid,
    )
    return _build_binary_frame(_Event.TASK_REQUEST, payload, session_id)


def _parse_frame(data: bytes) -> dict:
    """Parse a binary response frame from the server.

    Handles both Full-Server-Response (0b1001 — JSON payload with
    ``audio_data`` as base64) and Audio-Only-Response (0b1011 —
    raw binary audio data with no JSON wrapper).

    Returns dict with keys: event, session_id, payload, message_type
    """
    if not isinstance(data, bytes):
        raise ValueError(f"Expected bytes, got {type(data)}")
    if len(data) < 4:
        raise ValueError(f"Frame too short: {len(data)} bytes")

    message_type = (data[1] >> 4) & 0x0F
    flags = data[1] & 0x0F
    offset = 4  # skip fixed 4-byte header

    # Parse event number (present when flags & 0x04)
    event: Optional[int] = None
    if flags & _FLAG_HAS_EVENT and offset + 4 <= len(data):
        event = struct.unpack(">i", data[offset:offset + 4])[0]
        offset += 4

    # Parse session_id (present for server responses)
    session_id: Optional[str] = None
    if message_type in (_MSG_FULL_SERVER_RESPONSE, _MSG_AUDIO_ONLY_RESPONSE, _MSG_ERROR):
        if offset + 4 <= len(data):
            sid_len = struct.unpack(">I", data[offset:offset + 4])[0]
            offset += 4
            if sid_len > 0 and offset + sid_len <= len(data):
                session_id = data[offset:offset + sid_len].decode("utf-8", errors="replace")
                offset += sid_len

    # Parse payload based on message type
    payload = b""
    if offset + 4 > len(data):
        return {"event": event, "session_id": session_id, "payload": payload, "message_type": message_type}

    payload_len = struct.unpack(">I", data[offset:offset + 4])[0]
    offset += 4
    if message_type == _MSG_AUDIO_ONLY_RESPONSE:
        # Audio-only: raw audio data preceded by 4-byte length prefix
        if payload_len > 0 and offset + payload_len <= len(data):
            payload = data[offset:offset + payload_len]
    else:
        # Full server response: length prefix + JSON bytes
        if payload_len > 0 and offset + payload_len <= len(data):
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

    Authentication uses App-Id + Access-Key (console credentials) via
    ``X-Api-App-Id`` / ``X-Api-Access-Key`` headers.

    Requires ``VOLC_APP_ID`` and ``VOLC_ACCESS_TOKEN`` in .env.

    Resource ID is auto-detected from voice type:
      - Voices with ``_saturn_``, ``_uranus_``, or plain ``ICL_*_tob`` (no _v1)
        → uses ``seed-tts-2.0`` (TTS 2.0 / 豆包语音合成大模型2.0)
      - All other voices (``_mars_``, ``_moon_``, ``_audiobook_``, ``ICL_*_v1_tob``)
        → uses ``seed-tts-1.0`` (TTS 1.0)
    """

    # ── Resource ID helpers ──────────────────────────────────────────────

    @staticmethod
    def _detect_resource_id(voice_type: str) -> str:
        """Detect whether *voice_type* needs TTS 2.0 or TTS 1.0 resource."""
        # TTS 2.0 voices: *_saturn_*, *_uranus_*, ICL_*_tob (no _v1)
        if "_saturn_" in voice_type or "_uranus_" in voice_type:
            return "seed-tts-2.0"
        # ICL_*_tob without _v1 → TTS 2.0
        if "_tob" in voice_type and "_v1" not in voice_type:
            return "seed-tts-2.0"
        # Everything else → TTS 1.0
        return "seed-tts-1.0"

    def __init__(
        self,
        app_id: Optional[str] = None,
        access_token: Optional[str] = None,
        voice_type: str = "zh_female_vv_uranus_bigtts",
        sample_rate: int = 24000,
        audio_format: str = "mp3",
        api_url: str = _DEFAULT_API_ENDPOINT,
    ):
        self.app_id = app_id or settings.volc_app_id
        self.access_token = access_token or settings.volc_access_token
        self.voice_type = voice_type
        self.sample_rate = sample_rate
        self.audio_format = audio_format
        self.api_url = api_url
        self.resource_id = self._detect_resource_id(voice_type)

        if not self.app_id or not self.access_token:
            raise VolcTTSError(
                "Volcengine TTS requires VOLC_APP_ID and VOLC_ACCESS_TOKEN in .env"
            )

    # ------------------------------------------------------------------
    # Context manager for a full TTS WebSocket session
    # ------------------------------------------------------------------

    async def _run_session(self, text: str) -> bytes:
        """Execute a complete TTS session: connect → synthesize → disconnect.

        V3 bidirectional protocol flow (corrected):
          1. StartConnection  →  ConnectionStarted (50)
          2. StartSession     →  SessionStarted   (150)
          3. TaskRequest with full text
          4. Receive: SentenceStart (350), TTSResponse (352 with base64 audio
             or 0b1011 raw binary audio), SentenceEnd (351)
          5. FinishSession    →  SessionFinished  (152)
          6. FinishConnection →  ConnectionFinished (52)
        """
        if not text.strip():
            raise VolcTTSError("Cannot synthesize empty text")

        session_id = str(uuid.uuid4())
        audio_chunks: list[bytes] = []

        request_id = str(uuid.uuid4())
        headers = {
            "X-Api-App-Id": self.app_id,
            "X-Api-App-Key": self.app_id,
            "X-Api-Access-Key": self.access_token,
            "X-Api-Resource-Id": self.resource_id,
            "X-Api-Request-Id": request_id,
            "X-Api-Connect-Id": str(uuid.uuid4()),
        }
        user_uid = request_id

        try:
            async with asyncio.timeout(180):  # entire session max 3 min
                async with websockets.connect(
                    self.api_url,
                    additional_headers=headers,
                    max_size=16 * 1024 * 1024,
                    open_timeout=30,
                    ping_interval=20,
                    ping_timeout=20,
                    proxy=None,
                ) as ws:
                    # ── 1. StartConnection ──────────────────────────────────
                    await asyncio.wait_for(
                        ws.send(_build_empty_frame(_Event.START_CONNECTION)),
                        timeout=30,
                    )
                    resp = await asyncio.wait_for(ws.recv(), timeout=30)
                    parsed = _parse_frame(resp)
                    if parsed["event"] == _Event.CONNECTION_FAILED:
                        raise VolcTTSError(
                            f"Connection failed: "
                            f"{parsed['payload'].decode('utf-8', errors='replace')}"
                        )

                    # ── 2. StartSession (V3 format with namespace) ──────────
                    await asyncio.wait_for(ws.send(_build_start_session_frame(
                        session_id, self.voice_type,
                        self.audio_format, self.sample_rate,
                        user_uid=user_uid,
                    )), timeout=30)
                    resp = await asyncio.wait_for(ws.recv(), timeout=30)
                    parsed = _parse_frame(resp)
                    if parsed["event"] != _Event.SESSION_STARTED:
                        raise VolcTTSError(
                            f"Session failed to start: "
                            f"{parsed['payload'].decode('utf-8', errors='replace')}"
                        )

                    # ── 3. TaskRequest (send all text, V3 format) ──────────
                    await asyncio.wait_for(ws.send(_build_task_request_frame(
                        session_id, text, self.voice_type,
                        self.audio_format, self.sample_rate,
                        user_uid=user_uid,
                    )), timeout=30)

                    # ── 4. FinishSession (signal "no more text") ───────────
                    # Server starts streaming audio after FinishSession.
                    await asyncio.wait_for(
                        ws.send(_build_empty_frame(_Event.FINISH_SESSION, session_id)),
                        timeout=30,
                    )

                    # ── 5. Receive audio chunks ────────────────────────────
                    # Server sends AudioOnlyServer (0b1011) raw binary frames
                    # and/or FullServerResponse (0b1001) with base64 audio_data.
                    # Terminal events: SessionFinished (152) or TTSEnded (359).
                    session_done = False
                    while True:
                        resp = await asyncio.wait_for(ws.recv(), timeout=120)
                        parsed = _parse_frame(resp)

                        if parsed["message_type"] == _MSG_AUDIO_ONLY_RESPONSE:
                            # Raw binary audio data
                            if parsed["payload"]:
                                audio_chunks.append(parsed["payload"])

                        elif parsed["event"] == _Event.TTS_RESPONSE:
                            # JSON payload with base64-encoded audio_data
                            try:
                                json_data = json.loads(parsed["payload"])
                                audio_b64 = json_data.get("resp_params", {}).get("audio_data", "")
                                if audio_b64:
                                    audio_chunks.append(base64.b64decode(audio_b64))
                            except (json.JSONDecodeError, KeyError, ValueError):
                                pass

                        elif parsed["event"] in (_Event.TTS_SENTENCE_START,
                                                 _Event.TTS_SENTENCE_END):
                            continue  # progress frames, skip

                        elif parsed["event"] in (_Event.SESSION_FINISHED,
                                                 _Event.CONNECTION_FINISHED):
                            if parsed["event"] == _Event.SESSION_FINISHED:
                                session_done = True
                            break

                        elif parsed["event"] == _Event.SESSION_FAILED:
                            err = parsed["payload"].decode("utf-8", errors="replace")
                            raise VolcTTSError(f"Session failed: {err}")

                    # ── 6. FinishSession / FinishConnection cleanup ────────
                    if not session_done:
                        await asyncio.wait_for(
                            ws.send(_build_empty_frame(_Event.FINISH_SESSION, session_id)),
                            timeout=30,
                        )
                        try:
                            resp = await asyncio.wait_for(ws.recv(), timeout=5)
                        except asyncio.TimeoutError:
                            pass

                    await asyncio.wait_for(
                        ws.send(_build_empty_frame(_Event.FINISH_CONNECTION)),
                        timeout=30,
                    )

        except asyncio.TimeoutError:
            raise VolcTTSError(
                "TTS session timed out — network issue or invalid voice type?"
            )

        if not audio_chunks:
            raise VolcTTSError(
                "No audio data received from TTS server — "
                "check voice type and API key validity"
            )

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
