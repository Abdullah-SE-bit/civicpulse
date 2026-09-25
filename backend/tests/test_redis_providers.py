import fakeredis
from redis.exceptions import RedisError

from app.config import Settings
from app.providers.cache import RedisRateLimiter, RedisStatsCache, RedisTriageCache


class BrokenRedis:
    def __getattr__(self, name):
        def boom(*a, **k):
            raise RedisError("down")

        return boom


def test_stats_cache_round_trip_and_invalidate():
    c = RedisStatsCache(fakeredis.FakeRedis(decode_responses=True), 30)
    assert c.get() is None
    c.set('{"total": 1}')
    assert c.get() == '{"total": 1}'
    c.invalidate()
    assert c.get() is None


def test_stats_cache_ttl_is_set():
    r = fakeredis.FakeRedis(decode_responses=True)
    RedisStatsCache(r, 30).set("x")
    assert 0 < r.ttl("stats:v1") <= 30


def test_triage_cache_uses_24h_ttl_semantics():
    r = fakeredis.FakeRedis(decode_responses=True)
    c = RedisTriageCache(r)
    c.set("triage:k", "v", 86400)
    assert c.get("triage:k") == "v" and 86000 < r.ttl("triage:k") <= 86400


def test_every_cache_and_limiter_degrades_when_redis_is_down():
    broken = BrokenRedis()
    assert RedisTriageCache(broken).get("k") is None
    RedisTriageCache(broken).set("k", "v", 1)
    stats = RedisStatsCache(broken, 30)
    assert stats.get() is None
    stats.set("x")
    stats.invalidate()
    assert RedisRateLimiter(broken, 1).hit("ip") == (True, 0)  # fails open, logged


def test_limiter_counts_per_client_and_window():
    lim = RedisRateLimiter(fakeredis.FakeRedis(decode_responses=True), limit=2)
    assert [lim.hit("a")[0] for _ in range(3)] == [True, True, False]
    assert lim.hit("b")[0] is True  # other clients unaffected


def test_settings_treat_empty_env_as_unset():
    s = Settings.from_env({"DATABASE_URL": "", "REDIS_URL": "", "RATE_LIMIT_PER_MINUTE": ""})
    assert s.redis_url == "redis://redis:6379/0" and "@postgres:5432/" in s.database_url and s.rate_limit_per_minute == 20
