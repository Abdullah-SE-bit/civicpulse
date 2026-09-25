import json
from typing import Protocol

from app.domain import Category, Priority
from app.repositories.complaints import ComplaintRepository


class StatsCache(Protocol):
    def get(self) -> str | None: ...
    def set(self, payload: str) -> None: ...
    def invalidate(self) -> None: ...


class StatsService:
    """Read-through cache: TTL bounds staleness, explicit invalidation on write removes it."""

    def __init__(self, repo: ComplaintRepository, cache: StatsCache) -> None:
        self._repo = repo
        self._cache = cache

    def get(self) -> tuple[dict[str, object], str]:
        cached = self._cache.get()
        if cached is not None:
            return json.loads(cached), "HIT"
        stats = self._compute()
        self._cache.set(json.dumps(stats))
        return stats, "MISS"

    def _compute(self) -> dict[str, object]:
        by_category = self._repo.count_by("category")
        by_priority = self._repo.count_by("priority")
        return {
            "total": self._repo.total(),
            "by_category": {c.value: by_category.get(c.value, 0) for c in Category},
            "by_priority": {p.value: by_priority.get(p.value, 0) for p in Priority},
        }

    def invalidate(self) -> None:
        self._cache.invalidate()
