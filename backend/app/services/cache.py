"""
In-memory cache for frequent queries.
Caches LLM responses for identical (user_message + agent) combinations.
TTL: 15 minutes. Max entries: 200.

This avoids re-calling the LLM when multiple users ask the same thing
within a short window (e.g. "ventas del mes" asked by 3 people).
"""

import hashlib
import logging
import time
from datetime import datetime, timezone

logger = logging.getLogger("santonibot.cache")

_TTL_SECONDS = 15 * 60  # 15 minutes
_MAX_ENTRIES = 200

# Cache store: key → (response_text, agent_name, timestamp, data_timestamp)
_cache: dict[str, tuple[str, str, float, str]] = {}


def _make_key(message: str, department: str) -> str:
    """Create a cache key from message + department."""
    normalized = message.strip().lower()
    raw = f"{department}:{normalized}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _evict_expired() -> None:
    """Remove expired entries."""
    now = time.time()
    expired = [k for k, v in _cache.items() if now - v[2] > _TTL_SECONDS]
    for k in expired:
        del _cache[k]


def get_cached_response(message: str, department: str) -> dict | None:
    """
    Check cache for a matching response.
    Returns dict with response, agent_used, cached_at or None.
    """
    _evict_expired()
    key = _make_key(message, department)
    entry = _cache.get(key)
    if entry is None:
        return None

    response_text, agent_name, ts, data_ts = entry
    if time.time() - ts > _TTL_SECONDS:
        del _cache[key]
        return None

    logger.info("Cache HIT for '%s' (dept=%s)", message[:40], department)
    return {
        "response": response_text,
        "agent_used": agent_name,
        "cached_at": data_ts,
    }


def set_cached_response(
    message: str, department: str, response: str, agent_name: str
) -> None:
    """Store a response in cache."""
    # Evict + enforce max size
    _evict_expired()
    if len(_cache) >= _MAX_ENTRIES:
        # Remove oldest entry
        oldest_key = min(_cache, key=lambda k: _cache[k][2])
        del _cache[oldest_key]

    key = _make_key(message, department)
    now = time.time()
    data_ts = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
    _cache[key] = (response, agent_name, now, data_ts)
    logger.debug("Cache SET for '%s' (dept=%s)", message[:40], department)


def get_data_timestamp() -> str:
    """Return current timestamp for data freshness display."""
    now = datetime.now(timezone.utc)
    # Venezuela is UTC-4
    from datetime import timedelta
    ve_time = now - timedelta(hours=4)
    return ve_time.strftime("%d/%m/%Y, %I:%M %p")


def clear_cache() -> int:
    """Clear all cache entries. Returns count of cleared items."""
    count = len(_cache)
    _cache.clear()
    return count


def cache_stats() -> dict:
    """Return cache statistics."""
    _evict_expired()
    return {
        "entries": len(_cache),
        "max_entries": _MAX_ENTRIES,
        "ttl_seconds": _TTL_SECONDS,
    }
