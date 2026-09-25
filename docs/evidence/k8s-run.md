# Kubernetes evidence run

Real output of `scripts/evidence_k8s.sh` on a **kind** cluster inside a GitHub Actions runner (workflow `evidence-k8s`, run [36056340936](https://github.com/Abdullah-SE-bit/civicpulse/actions/runs/36056340936)). Nothing here is from a laptop or a managed cluster. Full transcript: [`k8s/k8s-transcript.txt`](k8s/k8s-transcript.txt). **22 checks passed, 0 failed.**

## Conditions (read these before using any number)
- One GitHub-hosted `ubuntu-latest` VM: 4 vCPU, about 16 GB RAM, running the whole kind cluster (one node), the ingress controller, the application **and k6 itself**. The load generator competes with the system under test, so absolute numbers are not representative of any real deployment and will vary run to run.
- kind v0.33.0, Kubernetes server v1.37.0, metrics-server v0.9.0 (`--kubelet-insecure-tls`, kind's kubelets use self-signed certificates), ingress-nginx controller v1.15.1, VPA 1.8.0 (recommender mode only).
- Overlay `k8s/overlays/dev` (images built in the job, `TRIAGE_PROVIDER=simulated`; irrelevant to the read load). Placeholder Secret from `k8s/secret.example.yaml`.
- Backend at the start: `requests: cpu 100m, memory 128Mi`, `limits: cpu 500m, memory 384Mi`; HPA `minReplicas 2`, `maxReplicas 10`, CPU target 60%, scale-up stabilization 0 s, scale-down 300 s.
- Load: `load/k6-script.js`, an open model (`ramping-arrival-rate`): 5 req/s for 30 s, ramp to **120 req/s** in 10 s, hold 240 s, drop to 5 req/s for 70 s. Endpoint: `GET /api/complaints?page=1&page_size=100` through the Ingress (33 seeded rows). The "offered load" line in the charts is k6's own count of completed requests per second, not the scheduled rate.

## What the cluster showed
| Item | Observed (from the transcript) |
|---|---|
| Namespace, workloads | everything in `civicpulse`; backend 2/2, frontend 2/2, redis 1/1 (Deployments), postgres 1/1 (StatefulSet) |
| Services | four, all `ClusterIP` (backend 8000, frontend 80, postgres 5432, redis 6379) |
| Storage | `pgdata-postgres-0` 1Gi and `redis-data` 256Mi, both `Bound` |
| Requests/limits | every container has cpu and memory requests and limits (checked programmatically) |
| PDB | `backend`, `minAvailable 1`, allowed disruptions 1 |
| Secret | `civicpulse-secrets`, listed by name only |
| Migration init container | log: `seeded 32 new complaints` (Alembic + seed ran once per pod start in the init container) |
| Ingress path | `/`, `/api/complaints` POST 201 and GET, `PATCH` 200 then invalid transition **409** `Invalid status transition: in_progress -> open`, `X-Cache: MISS` then `HIT`; no rewrite was needed |
| `/health`, `/ready` | 200 from inside a pod (port-forward) |
| `kubectl top` | works (`kubectl top nodes`, `kubectl top pods -n civicpulse`) |
| Postgres pod deleted | rows 33 before, 33 after; the created complaint still present |
| Redis scaled to 0 | backend pods `0/1 Running`, `endpoints backend` empty, `/ready` 503 `{"failed":"redis"}`, `/health` 200, **0 restarts**; recovered when Redis returned |

Two honest details: the HPA showed `cpu: <unknown>/60%` for its first ~80 s (metrics-server had no data yet), and it logs `FailedGetResourceMetric` warnings during the Redis-down test because pods that are not Ready are excluded from metrics.

## Load test and HPA (run 1: initial requests)
Charts: [`k8s/run1/hpa-replicas-vs-load.png`](k8s/run1/hpa-replicas-vs-load.png). Captured `kubectl get hpa -w`: [`k8s/run1/hpa-watch.txt`](k8s/run1/hpa-watch.txt). Sampled every 2 s: [`k8s/run1/timeline.csv`](k8s/run1/timeline.csv), [`rps.csv`](k8s/run1/rps.csv), k6 summary [`k6-summary.json`](k8s/run1/k6-summary.json).

- k6: 30,499 requests, **0 failed**, average 7.7 ms, p95 13.5 ms, max 280 ms.
- CPU went `19%` -> `104%` -> `315%` of the request, replicas `2 -> 4 -> 8 -> 10` (the scale-up policy allows +4 pods or +100% per 15 s).
- It reached `maxReplicas` and stayed there with CPU still around **72-75% (above the 60% target)**: at 120 req/s, ten pods at a 100m request were not enough to get under target. That is a capacity-planning result, not something the autoscaler could fix.
- Lag (`k8s/run1/lag.txt`, "load arrived" = first second k6 reached half of the configured 120 req/s):

| Milestone | Run 1 | Run 2 |
|---|---|---|
| HPA `desiredReplicas` > 2 | 27 s | 33 s |
| Deployment `spec.replicas` > 2 (scale applied) | 27 s | 33 s |
| first new pod `Ready` (`readyReplicas` > 2) | 36 s | 42 s |
| HPA `currentReplicas` > 2 (HPA status caught up) | 42 s | 48 s |
| max replicas | 10 | 9 |

Resolution is about 2 s (sampling interval). From these numbers alone: most of the lag (27-33 s) elapsed *before* the HPA decided anything, i.e. the metrics pipeline (metrics-server scrape, the HPA sync loop) plus the ramp itself; from decision to first ready pod took about 9 s in both runs, which includes the pod's `migrate` init container. Full capacity (10 pods) needed a second step because of the scale-up policy. What would shorten it is a hypothesis that was **not tested**: a shorter metrics resolution, a lower target or a higher `minReplicas`, and skipping migrations in scale-out pods.

## VPA and the second run
The VPA runs in recommender mode (`updateMode: "Off"`, `k8s/optional/vpa.yaml`). After run 1 it produced (transcript section 7):

| | Lower Bound | Target | Upper Bound |
|---|---|---|---|
| CPU | 64m | **163m** | 40709m |
| Memory | 250Mi | 250Mi | 18777003752 (bytes) |

**Treat this with suspicion.** The Upper Bound (about 40 CPU cores, 17.5 GiB) is a low-confidence artefact of only a few minutes of history, not a recommendation. The 250Mi memory figure looks like the recommender's default minimum rather than a measurement: `kubectl top` showed the backend at 67-74 Mi throughout. A different earlier run of the same setup ([run 36054916384](https://github.com/Abdullah-SE-bit/civicpulse/actions/runs/36054916384), earlier version of the script) produced a CPU target of **93m**, so the recommendation is not stable at this history length.

The script then applied only the CPU target (`kubectl set resources deploy/backend --requests=cpu=163m`; memory left at 128Mi request), reset the replicas to 2 and repeated the same load (run 2, charts and data in [`k8s/run2/`](k8s/run2/)):

- k6: 30,499 requests, 0 failed, average 7.3 ms, p95 11.7 ms, max 239 ms.
- Replicas `2 -> 4 -> 7 -> 9`, then **stable at 9 with CPU about 50-52%**, below the 60% target, versus 10 replicas at 72-75% in run 1.
- This is the HPA/VPA interaction in practice: HPA computes utilisation as usage / request. Raising the request from 100m to 163m lowered the reported utilisation for the same actual work, so the HPA needed fewer pods. Had the VPA been in `Auto` mode it would have made that change itself, and every change to the request moves the HPA's decision, which is why the two must not both manage CPU (ENGINEERING-NOTES 6).
- The apparent improvement (9 pods instead of 10, lower latency) is within what run-to-run variation on a shared runner could explain; one repetition per configuration is not enough to claim a performance gain.

## What was not done
- No `kubectl set image` rolling update under load (the zero-failed-requests bonus demo).
- No SIGTERM test on Kubernetes (Compose only, see `compose-run.md`), and no NetworkPolicy exists.
- The load generator shared the machine with the cluster; no repetition beyond the two runs above.
- `cd.yml`/`release.yml` have still not run.

## Repeat run
The same workflow was run again on a fresh runner from `dev` after later changes (workflow `evidence-k8s`, run [36099968739](https://github.com/Abdullah-SE-bit/civicpulse/actions/runs/36099968739)): 22 of 22 checks passed. Lag numbers, HPA capture, k6 summary and chart are in [`k8s-repeat/`](k8s-repeat/).

| | run 36056340936 run 1 | run 36056340936 run 2 | repeat run 1 | repeat run 2 |
|---|---|---|---|---|
| HPA decision, s after load arrived | 27 | 33 | 34 | 33 |
| first new pod Ready, s | 36 | 42 | 43 | 41 |
| max replicas | 10 | 9 | 10 | 9 |
| CPU request at start of the run | 100m | 163m (VPA target) | 100m | 109m (VPA target) |
| k6 requests / failed | 30,499 / 0 | 30,499 / 0 | 30,499 / 0 | 30,499 / 0 |

What repeats: a decision 27-34 s after the load arrives and a first Ready pod 36-43 s after (so about 8-9 s from decision to Ready every time), 10 replicas at the initial 100m request and 9 after applying the VPA CPU target. What does not: the VPA CPU target itself was **93m, 163m and 109m** in three runs of identical setup, so it is not a stable number at this history length, and the intermediate replica steps differed (`2 -> 4 -> 8 -> 10` in one run, `2 -> 6 -> 7 -> 10` in another). The latency figures (p95 7.2 ms in the repeat, 11.7-13.5 ms before) vary more between runs than between configurations, which is why no performance improvement is claimed from the second configuration.
