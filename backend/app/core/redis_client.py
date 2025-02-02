"""Redis connection, caching helpers, and idempotency locks."""

from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from typing import Any, Generator

from app.config import settings

logger = logging.getLogger(__name__)

_redis_client = None
_redis_disabled = False


def _disable_redis() -> None:
    global _redis_client, _redis_disabled
    _redis_client = None
    _redis_disabled = True


def get_redis():
    global _redis_client
    if _redis_disabled:
        return None
    if _redis_client is not None:
        return _redis_client

    try:
        from redis import Redis

        _redis_client = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
            health_check_interval=30,
        )
        return _redis_client
    except Exception:
        logger.exception("failed to initialize redis client")
        _disable_redis()
        return None


def ping_redis() -> bool:
    client = get_redis()
    if client is None:
        return False
    try:
        return bool(client.ping())
    except Exception:
        logger.warning("redis ping failed", exc_info=True)
        _disable_redis()
        return False


def get_cached_json(key: str) -> Any | None:
    client = get_redis()
    if client is None:
        return None
    try:
        value = client.get(key)
        return json.loads(value) if value else None
    except Exception:
        logger.warning("redis get failed", extra={"key": key}, exc_info=True)
        _disable_redis()
        return None


def set_cached_json(key: str, value: Any, ttl_seconds: int) -> bool:
    client = get_redis()
    if client is None:
        return False
    try:
        client.setex(key, ttl_seconds, json.dumps(value, default=str))
        return True
    except Exception:
        logger.warning("redis set failed", extra={"key": key}, exc_info=True)
        _disable_redis()
        return False


def delete_cache_key(key: str) -> None:
    client = get_redis()
    if client is None:
        return
    try:
        client.delete(key)
    except Exception:
        logger.warning("redis delete failed", extra={"key": key}, exc_info=True)
        _disable_redis()


def cache_task_result(task_id: str, summary: dict[str, Any], ttl_seconds: int | None = None) -> None:
    set_cached_json(
        f"task-summary:{task_id}",
        summary,
        ttl_seconds or settings.CELERY_TASK_RESULT_EXPIRES,
    )


def get_cached_task_result(task_id: str) -> dict[str, Any] | None:
    cached = get_cached_json(f"task-summary:{task_id}")
    return cached if isinstance(cached, dict) else None


@contextmanager
def redis_lock(key: str, ttl_seconds: int | None = None) -> Generator[bool, None, None]:
    client = get_redis()
    lock_value = "1"
    lock_ttl = ttl_seconds or settings.REDIS_LOCK_TTL_SECONDS

    if client is None:
        yield True
        return

    acquired = False
    try:
        acquired = bool(client.set(key, lock_value, nx=True, ex=lock_ttl))
        yield acquired
    except Exception:
        logger.warning("redis lock failed", extra={"key": key}, exc_info=True)
        _disable_redis()
        yield True
    finally:
        if acquired:
            try:
                client.delete(key)
            except Exception:
                logger.warning("redis lock release failed", extra={"key": key}, exc_info=True)
                _disable_redis()
