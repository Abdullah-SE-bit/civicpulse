# Triage cache: measured behaviour

Real output of `scripts/measure_triage_cache.py` against the Compose dev stack, with `scripts/measure.override.yaml` (simulated provider with a fixed 300 ms per inference, rate limit raised so it does not throttle the workload). Raw output: [triage-cache-measured.json](triage-cache-measured.json).

**Conditions.** Windows 11 laptop, Docker 29.8.0, Compose v5.5.1, current `dev`. Redis flushed before the run so the cache starts cold. **The workload is synthetic and chosen by me**: 12 distinct incidents (the first 12 seed complaints), reported 9, 6, 5, 4, 3, 3, 2, 2, 1, 1, 1, 1 times (38 requests), shuffled with a fixed seed. Repeat reports use cosmetic variants (upper/lower case, extra spaces), which the cache key normalises away. Each request came from a different client id, so the limiter was not involved.

## Result
| Measurement | Value |
|---|---|
| Requests | 38 |
| Cache misses (inferences paid) | **12** (= the number of distinct incidents) |
| Cache hits (inferences avoided) | **26** |
| **Hit rate for this workload** | **68.4 %** (26 / 38) |
| `triage:*` keys in Redis afterwards | 12 |
| Median client latency, miss | 341.5 ms (300 ms simulated inference plus HTTP and database) |
| Median client latency, hit | 51.1 ms |

The three sources agree: the app's own counters (26 hits, 12 misses), the number of keys in Redis (12), and the number of requests that paid the 300 ms (12 of 38). The script reports `consistent: true` only when they do.

## What this does and does not show
- It shows the design claim: a burst of duplicate reports costs one inference per *distinct* complaint, not one per report, and a hit is roughly 7x faster here because it skips the provider call.
- **The 68.4 % is a property of the workload I built, not a prediction for real traffic.** Any hit rate follows from how many duplicates arrive; I have no real traffic to measure. A run with no duplicates would give 0 %.
- The provider was `simulated` with an artificial 300 ms delay. No hosted LLM was called, so real inference latency and cost are not measured.
- The counters behind `/api/meta/providers` are per process since start (`services/meta.py`); with several replicas each reports its own tally, while the Redis cache itself is shared.

Reproduce: `docker compose -f compose.yaml -f scripts/measure.override.yaml up -d --build`, then `python scripts/measure_triage_cache.py` from the repo root (needs the backend directory for the seed texts).
