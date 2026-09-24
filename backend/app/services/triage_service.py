import hashlib
import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from app.providers.triage.base import RetryableTriageError, TriageProvider, TriageResult

log = logging.getLogger("civicpulse.triage")

CACHE_TTL_SECONDS = 24 * 3600


class TriageCache(Protocol):
    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str, ttl_seconds: int) -> None: ...


class DictCache:
    """In-process cache for tests; production uses a Redis-backed TriageCache."""

    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.data.get(key)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self.data[key] = value


@dataclass(frozen=True)
class TriageOutcome:
    result: TriageResult
    triaged_by: str
    latency_ms: int
    fallback: bool
    cache_hit: bool = False


def content_key(text: str, location: str) -> str:
    norm = " ".join(text.lower().split()) + "|" + " ".join(location.lower().split())
    return "triage:" + hashlib.sha256(norm.encode()).hexdigest()


def _ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


class TriageService:
    """Cache -> provider (one jittered retry on retryable errors) -> rules fallback."""

    def __init__(
        self,
        provider: TriageProvider,
        fallback: TriageProvider,
        cache: TriageCache | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._provider = provider
        self._fallback = fallback
        self._cache = cache
        self._sleep = sleep

    @property
    def provider_name(self) -> str:
        return self._provider.name

    def triage(self, text: str, location: str, complaint_id: str = "-") -> TriageOutcome:
        start = time.perf_counter()
        key = content_key(text, location)
        if self._cache is not None and (hit := self._cache.get(key)):
            cached_by, _, payload = hit.partition("\n")
            result = TriageResult.model_validate_json(payload)
            return TriageOutcome(result, cached_by, _ms(start), False, True)
        try:
            result = self._call(text, location)
            by, fell_back = self._provider.name, False
        except Exception as exc:  # noqa: BLE001 - any provider failure must degrade to rules, never surface
            log.warning(
                "triage fallback",
                extra={
                    "complaint_id": complaint_id,
                    "provider": self._provider.name,
                    "error_class": type(exc).__name__,
                },
            )
            result = self._fallback.triage(text, location)
            by, fell_back = "rules:fallback", True
        if self._cache is not None and not fell_back:
            self._cache.set(key, f"{by}\n{result.model_dump_json()}", CACHE_TTL_SECONDS)
        return TriageOutcome(result, by, _ms(start), fell_back)

    def _call(self, text: str, location: str) -> TriageResult:
        try:
            return self._provider.triage(text, location)
        except RetryableTriageError:
            self._sleep(random.uniform(0.1, 0.5))
            return self._provider.triage(text, location)
