import httpx
from loguru import logger

from src.core.config import settings

_client: httpx.AsyncClient | None = None


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=settings.waha_url,
            headers={"X-Api-Key": settings.waha_api_key},
            timeout=10.0,
        )
    return _client


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


async def subscribe_presence(chat_id: str) -> None:
    """Subscribe to typing/presence events for a contact. Non-critical."""
    client = await get_client()
    try:
        await client.post(f"/api/{settings.waha_session}/presence/{chat_id}/subscribe")
        logger.debug("Presence subscribed | chat_id={}", chat_id)
    except Exception as e:
        logger.debug("Presence subscribe skipped | chat_id={} reason={}", chat_id, e)


async def send_seen(chat_id: str) -> None:
    """Mark chat as read — customer sees double blue checkmarks immediately."""
    client = await get_client()
    try:
        await client.post(
            "/api/sendSeen",
            json={"session": settings.waha_session, "chatId": chat_id},
        )
        logger.debug("Seen sent | chat_id={}", chat_id)
    except Exception as e:
        logger.debug("sendSeen skipped | chat_id={} reason={}", chat_id, e)


async def start_typing(chat_id: str) -> None:
    """Show typing indicator to customer."""
    client = await get_client()
    try:
        await client.post(
            "/api/startTyping",
            json={"session": settings.waha_session, "chatId": chat_id},
        )
    except Exception as e:
        logger.debug("startTyping skipped | reason={}", e)


async def stop_typing(chat_id: str) -> None:
    """Hide typing indicator."""
    client = await get_client()
    try:
        await client.post(
            "/api/stopTyping",
            json={"session": settings.waha_session, "chatId": chat_id},
        )
    except Exception as e:
        logger.debug("stopTyping skipped | reason={}", e)


async def download_media(message_id: str) -> bytes | None:
    """Download media bytes for a given message ID. Returns None on failure."""
    client = await get_client()
    try:
        resp = await client.get(
            f"/api/{settings.waha_session}/messages/{message_id}/download",
        )
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        logger.warning("Media download failed | message_id={} error={}", message_id, e)
        return None


async def send_text(chat_id: str, text: str) -> None:
    client = await get_client()
    try:
        resp = await client.post(
            "/api/sendText",
            json={"session": settings.waha_session, "chatId": chat_id, "text": text},
        )
        resp.raise_for_status()
        logger.debug("WAHA sent | to={} chars={}", chat_id, len(text))
    except httpx.HTTPStatusError as e:
        logger.error("WAHA HTTP error | to={} status={} body={}", chat_id, e.response.status_code, e.response.text)
        raise
    except Exception as e:
        logger.error("WAHA send failed | to={} error={}", chat_id, e)
        raise
