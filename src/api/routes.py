import asyncio
import random
import time

from fastapi import APIRouter, BackgroundTasks
from loguru import logger

from src.api.models import WahaWebhookEvent, WahaMessagePayload
from src.core import waha_client
from src.core import state as state_manager
from src.core import sdr
from src.core import llm
from src.core import transcriber
from src.core.config import settings
from src.database import leads as leads_repo

router = APIRouter()

# Debounce config — industry standard for chat bots
_TYPING_BUFFER   = 3.0   # seconds to wait after typing stops before responding
_FALLBACK_WAIT   = 8.0   # if no presence events arrive, wait this long (NOWEB fallback)
_CHECK_INTERVAL  = 1.5   # how often to poll typing state
_MAX_WAIT        = 25.0  # never hold a response longer than this


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "dealer": settings.dealer_name}


@router.post("/webhook")
async def waha_webhook(event: WahaWebhookEvent, background_tasks: BackgroundTasks) -> dict:
    # ── Typing / presence events ──────────────────────────────────────────────
    if event.event == "presence.update":
        payload = event.payload if isinstance(event.payload, dict) else {}
        phone = payload.get("id", "")
        # WAHA sends either a single "presence" string or a list "presences"
        presences = payload.get("presences", [])
        presence_str = payload.get("presence", "")
        if presences and isinstance(presences, list):
            presence_str = presences[0].get("type", "") if presences else ""
        typing_active = presence_str in ("typing", "composing", "recording")
        if phone:
            await state_manager.set_typing(phone, typing_active)
            logger.debug("Presence | phone={} typing={}", phone, typing_active)
        return {"status": "ok"}

    # ── Message events ────────────────────────────────────────────────────────
    if event.event != "message":
        return {"status": "ignored"}

    payload = event.payload
    if isinstance(payload, dict):
        # Parse into proper model
        try:
            payload = WahaMessagePayload.model_validate(payload)
        except Exception:
            return {"status": "parse_error"}

    if payload.fromMe or payload.isGroup:
        return {"status": "filtered"}

    # Resolve message text — either plain body or transcribed audio
    text = (payload.body or "").strip()

    if not text and transcriber.is_audio_message(payload.type, payload.hasMedia):
        msg_id_for_dl = payload.id or ""
        if msg_id_for_dl:
            audio_bytes = await waha_client.download_media(msg_id_for_dl)
            if audio_bytes:
                text = await transcriber.transcribe(audio_bytes) or ""
                if text:
                    logger.info("Audio transcribed | phone={} text={!r}", payload.from_, text[:80])
                else:
                    logger.warning("Audio transcription empty | phone={}", payload.from_)

    if not text:
        return {"status": "filtered"}

    msg_id = payload.id or ""
    if msg_id and await state_manager.is_duplicate(msg_id):
        return {"status": "duplicate"}
    if msg_id:
        await state_manager.mark_processed(msg_id)

    phone = payload.from_

    # Mark as read immediately — customer sees blue checkmarks right away
    background_tasks.add_task(waha_client.send_seen, phone)
    # Subscribe to typing presence events for this contact
    background_tasks.add_task(waha_client.subscribe_presence, phone)

    # Queue message and schedule smart debounce handler
    arrival_ts = await state_manager.push_pending(phone, text)
    background_tasks.add_task(_smart_debounce, phone, arrival_ts)
    return {"status": "queued"}


async def _smart_debounce(phone: str, arrival_ts: float) -> None:
    """
    Wait until the customer stops typing, then add a short buffer before processing.
    Falls back to a fixed wait if no presence events are received (NOWEB limitation).
    """
    start         = time.time()
    received_typing_event = False

    while True:
        elapsed = time.time() - start

        # Safety valve — never wait forever
        if elapsed >= _MAX_WAIT:
            logger.debug("Debounce max wait reached | phone={}", phone)
            break

        # Abort if a newer message arrived after us
        latest_ts = await state_manager.get_latest_ts(phone)
        if latest_ts > arrival_ts:
            return

        currently_typing = await state_manager.is_typing(phone)
        if currently_typing:
            received_typing_event = True

        if currently_typing:
            # Customer is actively typing — keep polling
            await asyncio.sleep(_CHECK_INTERVAL)
            continue

        # Not typing. Decide how long to buffer:
        # - If we got real typing events: short buffer (3s) — we know they stopped
        # - If no events (NOWEB fallback): longer wait (8s) to simulate debounce
        wait = _TYPING_BUFFER if received_typing_event else _FALLBACK_WAIT
        await asyncio.sleep(wait)

        # Re-check after buffer — might have resumed typing or sent another message
        latest_ts = await state_manager.get_latest_ts(phone)
        if latest_ts > arrival_ts:
            return
        if await state_manager.is_typing(phone):
            received_typing_event = True
            continue  # Resumed — loop again

        break  # Confirmed done typing, buffer elapsed

    messages = await state_manager.drain_pending(phone)
    if not messages:
        return  # Already processed by a concurrent handler

    combined = "\n".join(messages)
    logger.info("Processing | phone={} parts={} text={!r}", phone, len(messages), combined[:80])
    await _handle_message(phone, combined)


def _typing_delay(text: str) -> float:
    """Simulate realistic typing time proportional to response length."""
    length = len(text)
    if length < 60:
        base = 1.2
    elif length < 160:
        base = 2.0
    else:
        base = 3.0
    return base + random.uniform(-0.3, 0.4)


async def _handle_message(phone: str, text: str) -> None:
    logger.info("Inbound | phone={} text={!r}", phone, text[:80])

    current_state = await state_manager.get_state(phone)
    step_before   = current_state.get("etapa", "")
    lang_before   = current_state.get("idioma", "EN")

    # Load conversation history so the LLM has full context
    history = await state_manager.get_history(phone)

    # Generate reply (LLM call with history)
    new_state, reply = await llm.chat(current_state, text, history)
    await state_manager.set_state(phone, new_state)

    # Persist this exchange to history for the next turn
    await state_manager.push_history(phone, "user", text)
    await state_manager.push_history(phone, "assistant", reply)

    try:
        await leads_repo.log_message(phone, "inbound", text, step_before, lang_before)
    except Exception as e:
        logger.warning("Failed to log inbound message | error={}", e)

    # Show typing indicator for a human-feeling delay, then send
    try:
        await waha_client.start_typing(phone)
        await asyncio.sleep(_typing_delay(reply))
        await waha_client.stop_typing(phone)
        await waha_client.send_text(phone, reply)
        await leads_repo.log_message(phone, "outbound", reply, new_state.get("etapa", ""), new_state.get("idioma", "EN"))
    except Exception as e:
        logger.error("Failed to send reply | phone={} error={}", phone, e)
        return

    if sdr.is_qualified(new_state):
        await _notify_vendor(phone, new_state)
        try:
            await leads_repo.upsert_lead(phone, new_state)
        except Exception as e:
            logger.error("Failed to save lead | phone={} error={}", phone, e)


async def _notify_vendor(phone: str, state: dict) -> None:
    vendor = settings.vendor_phone
    if not vendor:
        logger.warning("VENDOR_PHONE not set — skipping vendor notification")
        return
    card = sdr.build_lead_card(state, phone)
    vendor_chat_id = f"{vendor}@c.us" if "@" not in vendor else vendor
    try:
        await waha_client.send_text(vendor_chat_id, card)
        logger.info("Lead card sent to vendor | lead_phone={}", phone)
    except Exception as e:
        logger.error("Failed to notify vendor | error={}", e)
