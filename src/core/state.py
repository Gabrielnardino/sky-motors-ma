import json
import time
from typing import Any

import redis.asyncio as redis
from loguru import logger

from src.core.config import settings
from src.core.sdr import State, initial_state

_redis: redis.Redis | None = None

STATE_TTL = 86400    # 24h
MSG_DEDUP_TTL = 3600 # 1h
PENDING_TTL = 30     # max hold for debounce queue


def _key(phone: str) -> str:
    return f"state:{phone}"


def _msg_key(msg_id: str) -> str:
    return f"msg:{msg_id}"


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


async def get_state(phone: str) -> State:
    r = await get_redis()
    raw = await r.get(_key(phone))
    if raw:
        return json.loads(raw)
    logger.info("New conversation | phone={}", phone)
    return initial_state()


async def set_state(phone: str, state: State) -> None:
    r = await get_redis()
    await r.set(_key(phone), json.dumps(state), ex=STATE_TTL)


async def delete_state(phone: str) -> None:
    r = await get_redis()
    await r.delete(_key(phone))


async def is_duplicate(msg_id: str) -> bool:
    r = await get_redis()
    return bool(await r.exists(_msg_key(msg_id)))


async def mark_processed(msg_id: str) -> None:
    r = await get_redis()
    await r.set(_msg_key(msg_id), "1", ex=MSG_DEDUP_TTL)


# ---------------------------------------------------------------------------
# Debounce queue — holds messages while customer is still typing
# ---------------------------------------------------------------------------

def _pending_key(phone: str) -> str:
    return f"pending:{phone}"

def _pending_ts_key(phone: str) -> str:
    return f"pending_ts:{phone}"


async def push_pending(phone: str, text: str) -> float:
    """Append message to pending queue, update timestamp. Returns current timestamp."""
    r = await get_redis()
    ts = time.time()
    await r.rpush(_pending_key(phone), text)
    await r.expire(_pending_key(phone), PENDING_TTL)
    await r.set(_pending_ts_key(phone), str(ts), ex=PENDING_TTL)
    return ts


async def get_latest_ts(phone: str) -> float:
    """Return the timestamp of the most recently queued message."""
    r = await get_redis()
    val = await r.get(_pending_ts_key(phone))
    return float(val) if val else 0.0


async def drain_pending(phone: str) -> list[str]:
    """Atomically pop all pending messages. Returns empty list if already drained."""
    r = await get_redis()
    pipe = r.pipeline()
    pipe.lrange(_pending_key(phone), 0, -1)
    pipe.delete(_pending_key(phone), _pending_ts_key(phone))
    results = await pipe.execute()
    return results[0] or []


# ---------------------------------------------------------------------------
# Conversation history — keeps last N turns for LLM context
# ---------------------------------------------------------------------------

HISTORY_MAX_TURNS = 20   # 20 exchanges = 40 messages stored
HISTORY_TTL = 86400      # same as STATE_TTL


def _history_key(phone: str) -> str:
    return f"history:{phone}"


async def push_history(phone: str, role: str, content: str) -> None:
    """Append a message to conversation history. Trims to HISTORY_MAX_TURNS exchanges."""
    r = await get_redis()
    key = _history_key(phone)
    await r.rpush(key, json.dumps({"role": role, "content": content}))
    # Keep at most 2 * HISTORY_MAX_TURNS entries (each turn = user + assistant)
    await r.ltrim(key, -(HISTORY_MAX_TURNS * 2), -1)
    await r.expire(key, HISTORY_TTL)


async def get_history(phone: str) -> list[dict]:
    """Return conversation history as list of {role, content} dicts."""
    r = await get_redis()
    raw_list = await r.lrange(_history_key(phone), 0, -1)
    result = []
    for raw in raw_list:
        try:
            result.append(json.loads(raw))
        except Exception:
            pass
    return result


async def clear_history(phone: str) -> None:
    r = await get_redis()
    await r.delete(_history_key(phone))


# ---------------------------------------------------------------------------
# Typing presence state
# ---------------------------------------------------------------------------

TYPING_TTL = 30  # seconds — expire typing state if no update received


async def set_typing(phone: str, active: bool) -> None:
    r = await get_redis()
    key = f"typing:{phone}"
    if active:
        await r.set(key, "1", ex=TYPING_TTL)
    else:
        await r.delete(key)


async def is_typing(phone: str) -> bool:
    r = await get_redis()
    return bool(await r.exists(f"typing:{phone}"))
