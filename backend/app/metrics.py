from prometheus_client import Counter, Histogram

HTTP_REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "route", "status"])
HTTP_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency", ["method", "route"])
TRIAGE_LATENCY = Histogram(
    "triage_latency_seconds",
    "Triage latency",
    ["provider"],
    buckets=(0.005, 0.02, 0.1, 0.25, 0.5, 1, 2, 5, 10, 20),
)
TRIAGE_FALLBACKS = Counter("triage_fallback_total", "Triage fell back to rules", ["provider"])
TRIAGE_CACHE = Counter("triage_cache_total", "Triage content-hash cache lookups", ["result"])

# Per-process tallies behind /api/meta/providers (Prometheus counters cannot be read back cleanly).
cache_tally = {"hit": 0, "miss": 0}


def observe_triage(provider: str, triaged_by: str, latency_ms: int, fallback: bool, cache_hit: bool) -> None:
    result = "hit" if cache_hit else "miss"
    TRIAGE_CACHE.labels(result).inc()
    cache_tally[result] += 1
    if not cache_hit:
        TRIAGE_LATENCY.labels(triaged_by).observe(latency_ms / 1000)
    if fallback:
        TRIAGE_FALLBACKS.labels(provider).inc()
