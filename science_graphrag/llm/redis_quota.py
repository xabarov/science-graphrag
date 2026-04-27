"""Optional Redis-backed global LLM concurrency (Phase 5 / ADR 025).

Uses a ZSET of lease tokens scored by expiry time (ms). Process-local semaphores in
``concurrency.py`` acquire first; this module enforces the same numeric cap cluster-wide
when ``Settings.llm_distributed_quota_enabled`` is true.
"""

from __future__ import annotations

import logging
import re
import threading
import time
import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from science_graphrag.config import Settings

from science_graphrag.llm.pool_limits import pool_concurrency_limit

logger = logging.getLogger(__name__)

# KEYS[1] = zset key; ARGV: cap, ttl_ms, token, now_ms
_ACQUIRE_LUA = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[4])
local n = redis.call('ZCARD', KEYS[1])
if tonumber(n) >= tonumber(ARGV[1]) then
  return 0
end
redis.call('ZADD', KEYS[1], tonumber(ARGV[4]) + tonumber(ARGV[2]), ARGV[3])
return 1
"""

# KEYS[1] = zset; ARGV[1] = token
_RELEASE_LUA = """
return redis.call('ZREM', KEYS[1], ARGV[1])
"""


class DistributedQuotaAcquireTimeout(TimeoutError):
    """Distributed slot wait exceeded ``llm_distributed_quota_acquire_timeout_seconds``."""


def emit_distributed_quota_acquire_finished(
    pool_name: str,
    *,
    wait_ms: float,
    dist_token: str | None,
) -> None:
    """Phoenix span event: same contract for sync ``llm_pool_slot`` and async translation path."""

    try:
        from science_graphrag.observability.phoenix_tracer import add_span_event  # pylint: disable=import-outside-toplevel

        add_span_event(
            "llm.distributed_quota.acquire_finished",
            {
                "llm.distributed_quota.pool": pool_name,
                "llm.distributed_quota.wait_ms": round(float(wait_ms), 2),
                "llm.distributed_quota.fail_open": "1" if dist_token is None else "0",
            },
        )
    except Exception:  # noqa: BLE001
        pass


def emit_distributed_quota_fail_open(pool_name: str, reason: str) -> None:
    """Dedicated fail-open event when Redis errors force bypassing cluster-wide cap."""

    try:
        from science_graphrag.observability.phoenix_tracer import add_span_event  # pylint: disable=import-outside-toplevel

        msg = str(reason).strip()
        if len(msg) > 240:
            msg = msg[:237] + "..."
        add_span_event(
            "llm.distributed_quota.fail_open",
            {
                "llm.distributed_quota.pool": pool_name,
                "llm.distributed_quota.reason": msg,
            },
        )
    except Exception:  # noqa: BLE001
        pass


_CLIENT_LOCK = threading.Lock()
_CLIENT: Any = None
_CLIENT_SIG: tuple[str, float, float] | None = None
_SCRIPT_LOCK = threading.Lock()
_SCRIPTS: dict[int, tuple[Any, Any]] = {}
_CLIENT_OVERRIDE: Any = None


def set_quota_redis_client_override(client: object | None) -> None:
    """Tests only: force Redis client (e.g. FakeRedis) or clear override."""

    global _CLIENT_OVERRIDE  # pylint: disable=global-statement
    _CLIENT_OVERRIDE = client  # type: ignore[assignment]


def reset_quota_redis_client_for_tests() -> None:
    """Close cached client, clear overrides and script cache (tests)."""

    global _CLIENT, _CLIENT_SIG, _CLIENT_OVERRIDE  # pylint: disable=global-statement
    with _CLIENT_LOCK:
        if _CLIENT is not None:
            try:
                _CLIENT.close()
            except Exception:  # noqa: BLE001
                pass
        _CLIENT = None
        _CLIENT_SIG = None
    _CLIENT_OVERRIDE = None
    with _SCRIPT_LOCK:
        _SCRIPTS.clear()


def _sanitize_pool(pool_name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_]+", "_", str(pool_name).strip().lower())
    return s or "default"


def _zset_key(settings: "Settings", pool_name: str) -> str:
    prefix = str(settings.llm_distributed_quota_key_prefix or "").strip().rstrip(":")
    return f"{prefix}:z:{_sanitize_pool(pool_name)}"


def _redis_client(settings: "Settings") -> Any:
    global _CLIENT, _CLIENT_SIG  # pylint: disable=global-statement
    if _CLIENT_OVERRIDE is not None:
        return _CLIENT_OVERRIDE

    import redis as redis_mod_local  # pylint: disable=import-outside-toplevel

    connect_t = 2.0
    sock_t = 2.0
    sig = (str(settings.redis_url), connect_t, sock_t)
    with _CLIENT_LOCK:
        if _CLIENT is not None and _CLIENT_SIG == sig:
            return _CLIENT
        if _CLIENT is not None:
            try:
                _CLIENT.close()
            except Exception:  # noqa: BLE001
                pass
        _CLIENT = redis_mod_local.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=connect_t,
            socket_timeout=sock_t,
        )
        _CLIENT_SIG = sig
        with _SCRIPT_LOCK:
            _SCRIPTS.pop(id(_CLIENT), None)
        return _CLIENT


def _scripts(client: Any) -> tuple[Any, Any]:
    with _SCRIPT_LOCK:
        cid = id(client)
        if cid not in _SCRIPTS:
            _SCRIPTS[cid] = (
                client.register_script(_ACQUIRE_LUA),
                client.register_script(_RELEASE_LUA),
            )
        return _SCRIPTS[cid]


def try_acquire_once(settings: "Settings", pool_name: str, token: str) -> bool:
    """Single non-blocking acquire attempt; for tests and instrumentation."""

    client = _redis_client(settings)
    cap = pool_concurrency_limit(settings, pool_name)
    ttl_ms = max(1, int(settings.llm_distributed_quota_lease_seconds) * 1000)
    now_ms = int(time.time() * 1000)
    zkey = _zset_key(settings, pool_name)
    acquire_script, _ = _scripts(client)
    try:
        got = int(acquire_script(keys=[zkey], args=[cap, ttl_ms, token, now_ms]))
    except Exception as exc:  # noqa: BLE001
        logger.warning("llm distributed quota acquire skipped (redis error): %s", exc)
        return False
    return got == 1


def release_token(settings: "Settings", pool_name: str, token: str) -> None:
    """Release a held distributed slot (best-effort)."""

    if not settings.llm_distributed_quota_enabled and _CLIENT_OVERRIDE is None:
        return
    try:
        client = _redis_client(settings)
    except Exception as exc:  # noqa: BLE001
        logger.warning("llm distributed quota release skipped (redis client): %s", exc)
        return
    zkey = _zset_key(settings, pool_name)
    _, release_script = _scripts(client)
    try:
        release_script(keys=[zkey], args=[token])
    except Exception as exc:  # noqa: BLE001
        logger.warning("llm distributed quota release failed: %s", exc)


def acquire_slot_blocking(settings: "Settings", pool_name: str) -> str | None:
    """Block until a distributed slot is acquired or timeout.

    Returns a release token, ``None`` if distributed quota is disabled, or ``None`` on
    fail-open when Redis errors occur (caller proceeds without cluster-wide cap).
    Raises :class:`DistributedQuotaAcquireTimeout` if the wait budget is exhausted.
    """

    if not settings.llm_distributed_quota_enabled:
        return None

    try:
        client = _redis_client(settings)
    except Exception as exc:  # noqa: BLE001
        logger.warning("llm distributed quota fail-open (redis client): %s", exc)
        emit_distributed_quota_fail_open(pool_name, f"redis_client_error:{exc}")
        return None

    cap = pool_concurrency_limit(settings, pool_name)
    ttl_ms = max(1, int(settings.llm_distributed_quota_lease_seconds) * 1000)
    deadline = time.monotonic() + float(settings.llm_distributed_quota_acquire_timeout_seconds)
    zkey = _zset_key(settings, pool_name)
    acquire_script, _ = _scripts(client)
    token = str(uuid.uuid4())
    sleep_s = 0.05
    fail_open = False

    while time.monotonic() < deadline:
        now_ms = int(time.time() * 1000)
        try:
            got = int(acquire_script(keys=[zkey], args=[cap, ttl_ms, token, now_ms]))
        except Exception as exc:  # noqa: BLE001
            logger.warning("llm distributed quota fail-open (redis error): %s", exc)
            emit_distributed_quota_fail_open(pool_name, f"redis_eval_error:{exc}")
            fail_open = True
            break
        if got == 1:
            return token
        token = str(uuid.uuid4())
        time.sleep(sleep_s)

    if fail_open:
        return None
    raise DistributedQuotaAcquireTimeout(
        f"distributed LLM quota timeout pool={pool_name!r} cap={cap}",
    )
