import hashlib
from typing import Literal

from .base import (
    Category,
    Priority,
    RetryableTriageError,
    TriageError,
    TriageResult,
    parse_triage_json,
)

FailureMode = Literal["none", "raise", "retryable", "malformed"]


class SimulatedTriage:
    """Deterministic fake for CI: no network, output derived from a hash of the input."""

    name = "simulated"

    def __init__(self, failure: FailureMode = "none") -> None:
        self.failure = failure
        self.calls = 0

    def triage(self, text: str, location: str) -> TriageResult:
        self.calls += 1
        if self.failure == "raise":
            raise TriageError("injected failure")
        if self.failure == "retryable":
            raise RetryableTriageError("injected retryable failure")
        if self.failure == "malformed":
            return parse_triage_json('{"category": "not-a-category"}')
        digest = hashlib.sha256(f"{text}|{location}".encode()).digest()
        cats, prios = list(Category), list(Priority)
        return TriageResult(
            category=cats[digest[0] % len(cats)],
            priority=prios[digest[1] % len(prios)],
            summary=text.strip()[:100],
            confidence=round(digest[2] / 255, 2),
        )
