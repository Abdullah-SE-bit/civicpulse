# Compose evidence run

Real output of `scripts/evidence_compose.sh` against the dev stack (`compose.yaml` plus `scripts/evidence.override.yaml`, which runs the backend exactly as its image starts: no `--reload`, no source mount).

**Conditions.** A GitHub Actions runner, not a laptop: Linux 6.17 (azure) x86_64, Docker 28.0.4, Docker Compose v2.38.2, GitHub-hosted `ubuntu-latest`. Workflow `evidence` (`.github/workflows/evidence.yml`), run [36054209639](https://github.com/Abdullah-SE-bit/civicpulse/actions/runs/36054209639) on commit `11198f5`. Result: **46 PASS, 0 FAIL**. Full transcript (image-pull progress lines removed): [`compose-transcript.txt`](compose-transcript.txt).

**Honest note on how this was reached.** A first version of the script passed 40/40 but was weaker than it looked: its SIGTERM check only counted responses in a sequential loop (46 of 200 ended in `Connection reset by peer` after the process died, which the count could not distinguish from lost in-flight requests), and three `jq` lines silently failed. The version in this repository fixed those (a real in-flight request during shutdown, ordered-code analysis, visible isolation output) and produced the results below.

## What the run showed
| Claim | What the transcript shows |
|---|---|
| `docker compose config` valid | passes; services `postgres redis backend frontend` |
| Containers non-root, frontend has no Node | backend `uid=10001(app)`, frontend `uid=101(nginx)`; no `node`, no `node_modules`; `/usr/share/nginx/html` contains only `50x.html assets index.html` |
| Image sizes (final images) | backend **194 MB**, frontend **60.1 MB** (just over the ~60 MB the brief mentions as a warning sign; the size of the build stages was not measured) |
| Build contexts | four transfers reported: 129 B, 107 B, 55.30 kB, 170.22 kB (two per image; I did not attribute which is which, and there is no "before .dockerignore" measurement) |
| Health vs readiness | `/health` 200 and `/ready` 200 with everything up |
| Create / get / stats cache | POST through the frontend proxy returns 201, GET returns it; `/api/stats` `x-cache: MISS` then `HIT` |
| State machine | `open -> in_progress` 200; `in_progress -> open` **409** with body `Invalid status transition: in_progress -> open`; unknown id 404; invalid body 400 with per-field errors |
| Rate limit | 25 requests from one client: **20 x 201, 5 x 429**, `retry-after` header present; another client unaffected |
| Network isolation | `civicpulse_internal` has `internal=true`, members postgres, redis, backend; `civicpulse_edge` members frontend, backend. `frontend -> postgres`: `ping: bad address 'postgres'`; same for redis. Backend reaches postgres:5432 and redis:6379. Postgres has no outbound route; backend does (via `edge`) |
| Redis down | `/ready` 503 with `{"status":"unavailable","failed":"redis"}`; `/health` still 200; a POST still returns 201 (limiter fails open, caches miss); ready again after Redis restarts |
| Provider failure | backend started with `TRIAGE_PROVIDER=llm`, a dummy key and an unreachable endpoint: POST still 201, newest row `triaged_by = rules:fallback`, one `triage fallback` WARNING logged, metric `triage_fallback_total{provider="llm:groq"} 1.0` |
| Persistence | `docker compose down` (no `-v`) then `up`: total rows 56 before, 56 after; the created complaint still exists; volumes `civicpulse_pgdata`, `civicpulse_redisdata` |
| Graceful shutdown | a request whose 1.2 KB body was still uploading (300 B/s) when SIGTERM arrived: uvicorn logged `Shutting down` and `Waiting for connections to close`, completed the request, the client got **201** after the signal, then `Application shutdown complete`, exit code **0**; the row persisted. Requests started after the signal: 70 x 200 then only failures (80), never a success after a failure, no 5xx |

## What this does not show
- This is Compose on a runner. Nothing here was run on Kubernetes, and no HPA, VPA, load or scale-out result exists.
- The default `simulated` provider was used except in the provider-failure step; no real LLM was called. `category` values in the transcript come from a hash-based fake and are not a statement about classification quality.
- Not covered: malformed model output and prompt injection through Compose (both are unit-tested in `backend/tests/test_triage.py`); the runner's numbers are not laptop numbers.
