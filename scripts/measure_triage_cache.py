#!/usr/bin/env python3
"""Measure the content-hash triage cache on a running Compose stack.

Run from the repo root with the stack up using scripts/measure.override.yaml (simulated provider, 300 ms per
inference). The workload is synthetic and stated below: what is measured is that the cache does what the design
claims (duplicates cost one inference) and how much latency a hit saves. The hit *rate* is a property of the
workload, not a prediction for real traffic.
"""

import json
import random
import statistics
import subprocess
import sys
import time
import urllib.request

BACK = "http://localhost:8000"
sys.path.insert(0, "backend")
from app.seed_data import SEED_COMPLAINTS

# Reports per distinct incident: one burst main reported by nine neighbours, down to single reports.
REPORTS_PER_INCIDENT = [9, 6, 5, 4, 3, 3, 2, 2, 1, 1, 1, 1]


def variant(text: str, rng: random.Random) -> str:
    """Cosmetic differences a second reporter would introduce; the cache key normalises these away."""
    v = rng.choice([text, text.upper(), text.lower(), "  " + text + "  ", text.replace(" ", "  ", 1)])
    return v


def post(text: str, location: str, client: int) -> tuple[int, dict, float]:
    body = json.dumps({"text": text, "location": location}).encode()
    req = urllib.request.Request(
        f"{BACK}/api/complaints",
        data=body,
        headers={"Content-Type": "application/json", "X-Forwarded-For": f"198.51.100.{client}"},
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.loads(r.read())
    return r.status, payload, (time.perf_counter() - t0) * 1000


def get(path: str) -> dict:
    with urllib.request.urlopen(f"{BACK}{path}", timeout=10) as r:
        return json.loads(r.read())


def redis_triage_keys() -> int:
    out = subprocess.run(
        ["docker", "compose", "exec", "-T", "redis", "redis-cli", "--scan", "--pattern", "triage:*"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return len([line for line in out.splitlines() if line.strip()])


def main() -> None:
    rng = random.Random(42)
    incidents = SEED_COMPLAINTS[: len(REPORTS_PER_INCIDENT)]
    # a unique suffix per run so a rerun on a warm Redis volume still starts cold
    run_id = str(int(time.time()))
    work = []
    for (text, location, _cat, _prio), n in zip(incidents, REPORTS_PER_INCIDENT, strict=True):
        base = f"{text} (ref {run_id})"
        work += [(base, location, i) for i in range(n)]
    rng.shuffle(work)

    subprocess.run(["docker", "compose", "exec", "-T", "redis", "redis-cli", "flushall"], check=True, capture_output=True)
    before = get("/api/meta/providers")["triage_cache"]

    rows = []
    for k, (base, location, i) in enumerate(work):
        text = base if i == 0 else variant(base, rng)
        status, payload, ms = post(text, location, client=(k % 200) + 1)
        assert status == 201, status
        rows.append({"n": k + 1, "client_ms": round(ms, 1), "stored_triage_ms": payload["triage_latency_ms"]})

    meta = get("/api/meta/providers")
    after = meta["triage_cache"]
    hits = after["hits"] - before["hits"]
    misses = after["misses"] - before["misses"]
    total = hits + misses
    keys = redis_triage_keys()

    # misses pay the 300 ms inference; hits do not (stored_triage_ms is the time spent in triage itself)
    miss_ms = [r["client_ms"] for r in rows if r["stored_triage_ms"] >= 250]
    hit_ms = [r["client_ms"] for r in rows if r["stored_triage_ms"] < 250]
    result = {
        "conditions": {
            "provider": meta["active"],
            "simulated_inference_ms": 300,
            "requests": total,
            "distinct_incidents": len(REPORTS_PER_INCIDENT),
            "reports_per_incident": REPORTS_PER_INCIDENT,
        },
        "app_counters_this_run": {"hits": hits, "misses": misses, "hit_rate": round(hits / total, 3)},
        "redis_triage_keys": keys,
        "inferences_avoided": total - misses,
        "client_latency_ms": {
            "miss_median": round(statistics.median(miss_ms), 1) if miss_ms else None,
            "hit_median": round(statistics.median(hit_ms), 1) if hit_ms else None,
            "miss_n": len(miss_ms),
            "hit_n": len(hit_ms),
        },
        "consistent": hits + misses == total and misses == keys == len(REPORTS_PER_INCIDENT),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
