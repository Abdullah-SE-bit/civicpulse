import re

from .base import Category, Priority, TriageResult

_CATEGORY_KEYWORDS: list[tuple[Category, tuple[str, ...]]] = [
    (Category.streetlights, ("streetlight", "street light", "lamppost", "lamp post")),
    (Category.water, ("water", "pipe", "main", "flood", "leak", "tap", "paani")),
    (Category.electricity, ("electric", "power", "outage", "wire", "transformer", "bijli")),
    (Category.sanitation, ("garbage", "sewer", "drain", "trash", "waste", "kachra", "gutter")),
    (Category.roads, ("road", "pothole", "traffic", "bridge", "footpath", "sarak")),
]
_HIGH = ("burst", "flood", "fire", "danger", "sparking", "live wire", "collapse", "emergency")
_LOW = ("minor", "whenever", "cosmetic", "faded")


class RuleBasedTriage:
    """Deterministic keyword fallback. Always available, never raises on valid text."""

    name = "rules"

    def triage(self, text: str, location: str) -> TriageResult:
        lowered = text.lower()
        category = Category.other
        for cat, words in _CATEGORY_KEYWORDS:
            if any(w in lowered for w in words):
                category = cat
                break
        if any(w in lowered for w in _HIGH):
            priority = Priority.high
        elif any(w in lowered for w in _LOW):
            priority = Priority.low
        else:
            priority = Priority.normal
        first = re.split(r"(?<=[.!?])\s", text.strip(), maxsplit=1)[0]
        return TriageResult(
            category=category,
            priority=priority,
            summary=first[:140],
            confidence=0.4 if category is Category.other else 0.6,
        )
