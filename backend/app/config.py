import os
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    redis_url: str
    rate_limit_per_minute: int
    stats_ttl_seconds: int = 30

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if env is None else env
        return cls(
            database_url=env.get("DATABASE_URL")
            or "postgresql+psycopg://civicpulse:change-me@localhost:5432/civicpulse",
            redis_url=env.get("REDIS_URL") or "redis://localhost:6379/0",
            rate_limit_per_minute=int(env.get("RATE_LIMIT_PER_MINUTE") or "20"),
        )
