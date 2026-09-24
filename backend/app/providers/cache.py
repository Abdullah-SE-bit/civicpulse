"""Redis integrations: triage cache, stats cache and the distributed rate limiter."""

import logging
import time

from redis import Redis
from redis.exceptions import RedisError

log = logging.getLogger("civicpulse.redis")

STATS_KEY = "stats:v1"


def _text(value: object) -> str | None:
    if value is None:
        return None
    return value.decode() if isinstance(value, bytes) else str(value)


def make_redis(url: str) -> Redis:
    return Redis.from_url(url, decode_responses=True, socket_timeout=2, socket_connect_timeout=2)


class RedisTriageCache:
    """Content-hash triage cache. Redis being down degrades to 'no cache', never to an error."""

    def __init__(self, client: Redis) -> None:
        self._r = client

    def get(self, key: str) -> str | None:
        try:
            return _text(self._r.get(key))
        except RedisError:
            log.warning("triage cache read failed")
            return None

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        try:
            self._r.set(key, value, ex=ttl_seconds)
        except RedisError:
            log.warning("triage cache write failed")


class RedisStatsCache:
    def __init__(self, client: Redis, ttl_seconds: int) -> None:
        self._r = client
        self._ttl = ttl_seconds

    def get(self) -> str | None:
        try:
            return _text(self._r.get(STATS_KEY))
        except RedisError:
            log.warning("stats cache read failed")
            return None

    def set(self, payload: str) -> None:
        try:
            self._r.set(STATS_KEY, payload, ex=self._ttl)
        except RedisError:
            log.warning("stats cache write failed")

    def invalidate(self) -> None:
        try:
            self._r.delete(STATS_KEY)
        except RedisError:
            log.warning("stats cache invalidation failed")


class RedisRateLimiter:
    """Fixed-window counter shared by every replica, keyed by client and window."""

    def __init__(self, client: Redis, limit: int, window_seconds: int = 60) -> None:
        self._r = client
        self._limit = limit
        self._window = window_seconds

    def hit(self, client_id: str) -> tuple[bool, int]:
        """Returns (allowed, retry_after_seconds). Fails open if Redis is unreachable."""
        now = int(time.time())
        bucket = now // self._window
        key = f"rl:{client_id}:{bucket}"
        try:
            pipe = self._r.pipeline()
            pipe.incr(key)
            pipe.expire(key, self._window)
            count = int(pipe.execute()[0])
        except RedisError:
            log.warning("rate limiter unavailable, failing open")
            return True, 0
        if count > self._limit:
            return False, (bucket + 1) * self._window - now
        return True, 0

    def ping(self) -> None:
        self._r.ping()
