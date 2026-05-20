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
        _redis = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
        )
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


async def _reset_redis() -> redis.Redis:
    """Force reconnect — called when connection is stale after infra restart."""
    global _redis
    if _redis:
        try:
            await _redis.aclose()
        except Exception:
            pass
    _redis = None
    return await get_redis()


async def _exec(fn):
    """Execute a Redis operation, auto-reconnecting once on timeout."""
    try:
        r = await get_redis()
        return await fn(r)
    except (redis.exceptions.TimeoutError, redis.exceptions.ConnectionError) as e:
        logger.warning("Redis connection lost, reconnecting | error={}", e)
        r = await _reset_redis()
        return await fn(r)


async def get_state(phone: str) -> State:
    raw = await _exec(lambda r: r.get(_key(phone)))
    if raw:
        return json.loads(raw)
    logger.info("New conversation | phone={}", phone)
    return initial_state()


async def set_state(phone: str, state: State) -> None:
    await _exec(lambda r: r.set(_key(phone), json.dumps(state), ex=STATE_TTL))


async def delete_state(phone: str) -> None:
    await _exec(lambda r: r.delete(_key(phone)))


async def is_duplicate(msg_id: str) -> bool:
    return bool(await _exec(lambda r: r.exists(_msg_key(msg_id))))


async def mark_processed(msg_id: str) -> None:
    await _exec(lambda r: r.set(_msg_key(msg_id), "1", ex=MSG_DEDUP_TTL))


# ---------------------------------------------------------------------------
# Debounce queue — holds messages while customer is still typing
# ---------------------------------------------------------------------------

def _pending_key(phone: str) -> str:
    return f"pending:{phone}"

def _pending_ts_key(phone: str) -> str:
    return f"pending_ts:{phone}"


async def push_pending(phone: str, text: str) -> float:
    ts = time.time()
    async def _push(r):
        await r.rpush(_pending_key(phone), text)
        await r.expire(_pending_key(phone), PENDING_TTL)
        await r.set(_pending_ts_key(phone), str(ts), ex=PENDING_TTL)
    await _exec(_push)
    return ts


async def get_latest_ts(phone: str) -> float:
    val = await _exec(lambda r: r.get(_pending_ts_key(phone)))
    return float(val) if val else 0.0


async def drain_pending(phone: str) -> list[str]:
    async def _drain(r):
        pipe = r.pipeline()
        pipe.lrange(_pending_key(phone), 0, -1)
        pipe.delete(_pending_key(phone), _pending_ts_key(phone))
        results = await pipe.execute()
        return results[0] or []
    return await _exec(_drain)


# ---------------------------------------------------------------------------
# Typing presence state
# ---------------------------------------------------------------------------

TYPING_TTL = 30


async def set_typing(phone: str, active: bool) -> None:
    key = f"typing:{phone}"
    if active:
        await _exec(lambda r: r.set(key, "1", ex=TYPING_TTL))
    else:
        await _exec(lambda r: r.delete(key))


async def is_typing(phone: str) -> bool:
    return bool(await _exec(lambda r: r.exists(f"typing:{phone}")))
