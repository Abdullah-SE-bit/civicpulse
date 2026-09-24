from dataclasses import dataclass

from redis import Redis
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.providers.cache import RedisRateLimiter, RedisStatsCache, RedisTriageCache
from app.providers.triage.base import TriageProvider
from app.providers.triage.rules import RuleBasedTriage
from app.services.triage_service import TriageService


@dataclass
class Container:
    """Composition root: everything the request handlers are wired from."""

    settings: Settings
    engine: Engine
    session_factory: sessionmaker[Session]
    redis: Redis
    triage: TriageService
    stats_cache: RedisStatsCache
    limiter: RedisRateLimiter


def build_container(
    settings: Settings,
    engine: Engine,
    session_factory: sessionmaker[Session],
    redis: Redis,
    provider: TriageProvider,
) -> Container:
    return Container(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
        redis=redis,
        triage=TriageService(provider, RuleBasedTriage(), RedisTriageCache(redis)),
        stats_cache=RedisStatsCache(redis, settings.stats_ttl_seconds),
        limiter=RedisRateLimiter(redis, settings.rate_limit_per_minute),
    )
