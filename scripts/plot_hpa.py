"""Build the replicas-vs-offered-load chart and the lag numbers from the raw capture. No data is synthesised.

Inputs (written by scripts/evidence_k8s.sh):
  timeline.csv  epoch,current,desired,ready,cpu_pct   sampled every 2 s from `kubectl get hpa/deploy`
  k6.csv        k6 --out csv, filtered to the http_reqs metric (metric_name,timestamp,metric_value,...)
Outputs: rps.csv, hpa-replicas-vs-load.png, lag.txt
"""

import csv
import sys
from collections import Counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

MIN_REPLICAS = 2

rows = list(csv.DictReader(open("timeline.csv")))
t = [int(r["epoch"]) for r in rows]
current = [int(r["current"] or 0) for r in rows]
desired = [int(r["desired"] or 0) for r in rows]
ready = [int(r["ready"] or 0) for r in rows]
cpu = [float(r["cpu_pct"]) if r["cpu_pct"] not in ("", "<none>") else None for r in rows]

per_sec = Counter()
with open("k6.csv") as f:
    for r in csv.DictReader(f):
        if r["metric_name"] == "http_reqs":
            per_sec[int(float(r["timestamp"]))] += 1
with open("rps.csv", "w") as f:
    f.write("epoch,rps\n")
    for k in sorted(per_sec):
        f.write(f"{k},{per_sec[k]}\n")

peak = max(per_sec.values())
# Load "arrives" at the first second the offered rate reaches half of its peak.
t_load = min(k for k, v in per_sec.items() if v >= peak / 2)


def first(cond):
    for ts, *vals in zip(t, current, desired, ready):
        if ts >= t_load and cond(*vals):
            return ts
    return None


t_desired = first(lambda c, d, r: d > MIN_REPLICAS)
t_current = first(lambda c, d, r: c > MIN_REPLICAS)
t_ready = first(lambda c, d, r: r > MIN_REPLICAS)
lines = [
    f"offered load: peak {peak} req/s; half-peak first reached at epoch {t_load}",
    f"HPA desiredReplicas > {MIN_REPLICAS}: {t_desired and t_desired - t_load} s after load arrived",
    f"HPA currentReplicas > {MIN_REPLICAS}: {t_current and t_current - t_load} s after load arrived",
    f"Deployment readyReplicas > {MIN_REPLICAS}: {t_ready and t_ready - t_load} s after load arrived",
    f"max replicas observed: {max(current)}",
    "sampling interval 2 s, so each figure has roughly +/- 2 s resolution",
]
open("lag.txt", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))

t0 = min(t[0], min(per_sec))
fig, ax1 = plt.subplots(figsize=(10, 5))
ks = sorted(per_sec)
ax1.plot([k - t0 for k in ks], [per_sec[k] for k in ks], color="tab:blue", label="offered load (req/s, from k6 http_reqs)")
ax1.set_xlabel("seconds since capture start")
ax1.set_ylabel("requests per second", color="tab:blue")
ax2 = ax1.twinx()
ax2.step([x - t0 for x in t], current, where="post", color="tab:red", label="HPA currentReplicas")
ax2.step([x - t0 for x in t], ready, where="post", color="tab:green", linestyle="--", label="Deployment readyReplicas")
ax2.step([x - t0 for x in t], desired, where="post", color="tab:orange", linestyle=":", label="HPA desiredReplicas")
ax2.set_ylabel("backend replicas")
ax2.set_ylim(0, max(current + desired) + 1)
ax1.axvline(t_load - t0, color="grey", linestyle=":", linewidth=1)
h1, l1 = ax1.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, loc="upper right", fontsize=8)
plt.title("Backend replicas vs offered load (kind on a GitHub runner; measured)")
plt.tight_layout()
plt.savefig("hpa-replicas-vs-load.png", dpi=130)
sys.exit(0)
