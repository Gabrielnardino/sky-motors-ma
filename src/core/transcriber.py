"""
Audio transcription via Groq Whisper.
Accepts raw audio bytes (ogg/mp4/webm — WhatsApp formats) and returns text.
"""
from __future__ import annotations
import io
from loguru import logger
from groq import AsyncGroq

from src.core.config import settings

_client: AsyncGroq | None = None

_AUDIO_TYPES = {"ptt", "audio"}  # WhatsApp message types that carry voice


def get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


def is_audio_message(msg_type: str | None, has_media: bool) -> bool:
    return has_media and msg_type in _AUDIO_TYPES


async def transcribe(audio_bytes: bytes, filename: str = "audio.ogg") -> str | None:
    """
    Transcribe audio bytes using Groq Whisper.
    Returns transcribed text, or None on failure.
    Whisper auto-detects PT/ES/EN — no language hint needed.
    """
    if not settings.groq_api_key:
        logger.warning("GROQ_API_KEY not set — audio transcription disabled")
        return None

    try:
        client = get_client()
        audio_file = (filename, io.BytesIO(audio_bytes), "audio/ogg")
        result = await client.audio.transcriptions.create(
            model="whisper-large-v3-turbo",
            file=audio_file,
            response_format="text",
        )
        text = result.strip() if isinstance(result, str) else str(result).strip()
        logger.info("Audio transcribed | chars={} preview={!r}", len(text), text[:60])
        return text or None
    except Exception as e:
        logger.error("Groq transcription failed | error={}", e)
        return None
