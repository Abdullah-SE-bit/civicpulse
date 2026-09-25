from app import metrics
from app.repositories.complaints import ComplaintRepository

FALLBACK = "rules:fallback"


def provider_meta(repo: ComplaintRepository, active: str) -> dict[str, object]:
    hits, misses = metrics.cache_tally["hit"], metrics.cache_tally["miss"]
    lookups = hits + misses
    return {
        "active": active,
        "recent": [
            {"provider": by, "latency_ms": ms, "fallback": by == FALLBACK}
            for by, ms in repo.recent_triage(20)
        ],
        "triage_cache": {
            "hits": hits,
            "misses": misses,
            "hit_rate": round(hits / lookups, 3) if lookups else None,
            "scope": "this process since start",
        },
    }
