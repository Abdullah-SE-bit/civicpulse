# AI Usage Disclosure

Per assignment §5.5, AI assistance is disclosed here. Each entry is appended as work happens; nothing is back-filled from memory.

**Tool:** Claude Code (Anthropic), run in two separate sessions: ALPHA (GitHub account `Abdullah-SE-bit`) and BETA (GitHub account `rayyanhasan899`).

## Log

| Date | Tool / session | Area affected | Changes made by AI | Reviewed / modified by the team |
|------|----------------|---------------|--------------------|---------------------------------|
| 2026-09-24 | Claude Code / ALPHA | Repo bootstrap | Directory scaffold, .gitignore, .env.example, README, doc skeletons, LICENSE | _pending review_ |
| 2026-09-25 | Claude Code / BETA | frontend eslint config and component tests | Added eslint, 7 component/client tests, refactored Dashboard fetch effect to fix a lint error | _pending review_ |
| 2026-09-25 | Claude Code / BETA | docs/ROLLBACK.md | Wrote the rollback runbook | _pending review_ (commands not run: no cluster available) |
| 2026-09-24 | Claude Code / BETA | k8s/ manifests, cd.yml, release.yml, scripts/kind-config.yaml, notes Q6 | Wrote Kustomize base + overlays, optional VPA, CD and release workflows | _pending review_ (YAML parse only; no cluster, kubectl or runner available) |
| 2026-09-24 | Claude Code / BETA | compose.yaml, compose.prod.yaml, notes Q7 | Wrote both Compose files and two notes paragraphs | _pending review_ (YAML parse only; not run, Docker unavailable) |
| 2026-09-24 | Claude Code / BETA | .github/workflows/ci.yml, scripts/integration.sh | Wrote CI workflow and integration script | _pending review_ (never run on a runner yet; YAML parse + bash -n only) |
| 2026-09-24 | Claude Code / BETA | Frontend (React+Vite+TS), nginx.conf, frontend Dockerfile, ADR 0001 | Wrote all frontend source, client, one validation test, Dockerfile, nginx config, ADR | _pending review_ (image build not yet run: Docker unavailable locally) |
| 2026-09-24 | Claude Code / ALPHA | Backend triage layer | Providers (rules, simulated, LLM, Ollama), factory, TriageService (retry, fallback, cache), tests | _pending review by BETA_ |
| 2026-09-25 | Claude Code / ALPHA | Backend data layer | Domain enums and state machine, models, Alembic migration, repository, ComplaintService, idempotent seed, backend Dockerfile and entrypoint, tests | _pending review by BETA_ |
| 2026-09-25 | Claude Code / ALPHA | Backend HTTP API | FastAPI app, routes, Redis stats cache + rate limiter + triage cache, health/ready/metrics, JSON logging, API tests | _pending review by BETA_ |



## Rules we follow
- AI output is reviewed before merge; a line nobody can explain is not merged.
- No secrets are ever given to an AI tool or committed.
