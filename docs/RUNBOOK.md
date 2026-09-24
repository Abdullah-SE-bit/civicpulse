# Runbook

> **Status of this document:** the commands are written from the manifests and code. None of the Docker, Compose or Kubernetes commands below have been run yet (Docker was not installed on the machine that wrote it). Treat them as the intended procedure and correct this file the first time one does not behave as written.

Service names: `frontend` (nginx, port 8080), `backend` (FastAPI, 8000), `postgres` (5432), `redis` (6379), optional `ollama` (11434). Kubernetes namespace: `civicpulse`.

## Start locally (Compose)
```bash
cp .env.example .env            # placeholders only; edit POSTGRES_PASSWORD and DATABASE_URL together
docker compose up --build       # dev stack; add --profile ollama for the offline model
docker compose ps               # every service should become "healthy"
```
Open http://localhost:8080. The backend entrypoint runs `alembic upgrade head` and the idempotent seed on start (`backend/entrypoint.sh`).

Production-style stack (prebuilt images, no source mount, no published DB/cache/backend ports):
```bash
IMAGE_TAG=<commit-sha> docker compose -f compose.prod.yaml up -d
```

## Deploy to Kubernetes (kind)
```bash
kind create cluster --name civicpulse --config scripts/kind-config.yaml
# ingress-nginx and metrics-server: see the "Install ingress-nginx and metrics-server" step in .github/workflows/cd.yml
kubectl create namespace civicpulse
kubectl apply -f k8s/secret.example.yaml         # placeholders, fine for a throwaway local cluster only
kind load docker-image ghcr.io/abdullah-se-bit/civicpulse-backend:dev ghcr.io/abdullah-se-bit/civicpulse-frontend:dev --name civicpulse
kubectl apply -k k8s/overlays/dev
kubectl -n civicpulse rollout status deployment/backend deployment/frontend
```
Real environments: create the Secret from real values (`kubectl create secret generic civicpulse-secrets ...`, see the comment in `k8s/secret.example.yaml`); never commit it.

## Is it healthy?
| Check | Command | Meaning |
|---|---|---|
| Liveness | `curl localhost:8000/health` (Compose) | process is up; deliberately does not touch Postgres |
| Readiness | `curl -i localhost:8000/ready` | 200 only if Postgres and Redis both answer; otherwise 503 naming the failed dependency |
| Pods | `kubectl -n civicpulse get pods,hpa,pdb` | `READY 1/1`; the HPA `TARGETS` must show a percentage, not `<unknown>` |
| Provider | `curl localhost:8000/api/meta/providers` | active provider, last 20 triage outcomes, this process's cache tally |
| Metrics | `curl localhost:8000/metrics` | Prometheus text: request count/latency, triage latency, fallback counter |

In Kubernetes the backend is not published; use `kubectl -n civicpulse port-forward deployment/backend 8000:8000` for these.

## Logs
Logs are JSON on stdout with a `request_id` on every line.
```bash
docker compose logs -f backend
kubectl -n civicpulse logs deployment/backend --all-containers -f
kubectl -n civicpulse logs deployment/backend -c migrate      # the migration/seed init container
```
Follow one request: take the id from an `X-Request-ID` header (nginx sets one if the client did not) and grep for it.

## Triage is failing or looks wrong
1. `GET /api/meta/providers`: `active` shows the configured provider; `recent` shows `fallback: true` rows.
2. Look for the WARNING `triage fallback` in the backend logs: it carries `complaint_id`, `provider` and `error_class` (never the key or the text).
3. `error_class` decides the cause: `RetryableTriageError` = timeout, 429 or 5xx from the provider (retried once, then fell back); `TriageError` = a 4xx (bad key, bad model name) or output that failed schema validation (not retried).
4. Complaints keep being created with `triaged_by = rules:fallback`; nothing is lost, only quality. Fix the cause (key, model name, provider status) and new complaints recover on their own; existing rows are not re-triaged.
5. If `TRIAGE_PROVIDER=llm` and `LLM_API_KEY` is empty, the backend deliberately serves plain `rules` and logs a warning at startup (`providers/triage/factory.py`): check the Secret.
6. To rule the provider out entirely, set `TRIAGE_PROVIDER=rules` or `simulated`.

## Redis problems
- `/ready` returns 503 naming redis: the backend pod leaves the Service until Redis returns (readiness), it is not restarted (liveness is independent).
- With Redis down the app degrades rather than fails: triage cache and stats cache act as misses and the rate limiter fails open (`providers/cache.py`), each with a WARNING. That also means **no rate limiting** while Redis is down.
- Check: `docker compose exec redis redis-cli ping` or `kubectl -n civicpulse exec deploy/redis -- redis-cli ping`. Data: AOF on the `redisdata` volume / `redis-data` PVC.
- Stats look stale after a write: they are invalidated on write and expire after 30 s; confirm with the `X-Cache` header on `/api/stats`.

## Postgres problems
- `/ready` 503 naming postgres. `kubectl -n civicpulse get pods -l app=postgres`, `kubectl -n civicpulse describe pod postgres-0`, check the PVC is `Bound`: `kubectl -n civicpulse get pvc`.
- Data survives deleting the pod because it is a StatefulSet with a `volumeClaimTemplate` (`k8s/base/postgres.yaml`); Compose uses the `pgdata` volume. `docker compose down` keeps it; **`docker compose down -v` deletes it.**
- Schema problems: migrations are Alembic only. `kubectl -n civicpulse logs deployment/backend -c migrate`.

## Which image is running?
The tag is the commit SHA.
```bash
kubectl -n civicpulse get deploy backend frontend -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.template.spec.containers[0].image}{"\n"}{end}'
git show <sha> --stat
```

## Roll back
See [ROLLBACK.md](ROLLBACK.md): `kubectl rollout undo` for speed, re-apply the overlay with a previous SHA (or `git revert`) for an auditable record.

## Recover from a failed deployment
1. `kubectl -n civicpulse rollout status deployment/backend` and `kubectl -n civicpulse get pods`.
2. Pods `CrashLoopBackOff`: `kubectl -n civicpulse logs <pod> --previous`. Stuck in `Init`: the `migrate` container failed, see its logs (usually a wrong `DATABASE_URL` in the Secret or Postgres not ready).
3. Pods running but not `Ready`: `/ready` is failing, so Postgres or Redis is unreachable; see the sections above.
4. `ImagePullBackOff`: the SHA tag was never pushed (the `build-push` job failed) or the cluster cannot pull from GHCR.
5. If users are affected now: `kubectl -n civicpulse rollout undo deployment/backend`. The rolling-update settings (`maxUnavailable: 0`) keep old pods serving until new ones are ready, so a bad rollout normally stalls rather than takes the service down.

## Common CI failures
| Symptom | Cause |
|---|---|
| `Unable to resolve action ...` | an action tag that does not exist (Trivy's tags are `v`-prefixed; this happened here). Check with `gh api repos/<owner>/<action>/tags` |
| `lint-and-type` fails | run `ruff check .` and `mypy app` in `backend/`, `npm run lint` and `npx tsc --noEmit` in `frontend/` |
| `build` fails at Trivy | a HIGH/CRITICAL finding with a fix available: update the base image or dependency; do not suppress blindly |
| `manifests` fails | reproduce with `kubectl kustomize k8s/overlays/prod \| kubeconform -strict -ignore-missing-schemas -` |
| `integration` fails | see the uploaded `docker compose logs` at the end of the job; run `scripts/integration.sh` against a local stack |
