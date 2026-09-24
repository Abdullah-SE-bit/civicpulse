# CivicPulse

End-to-end municipal complaint intake, triage and operations platform. Citizens submit free-text complaints; the backend triages them (category, priority, one-line summary) through a replaceable `TriageProvider`, persists them in PostgreSQL, and an operations dashboard shows them with cached aggregate stats.

**Status:** repository bootstrap. No application code yet; the quickstart below will be added once it works from a clean clone.

## Planned stack
React 18 + Vite + TypeScript (nginx) | FastAPI + Pydantic v2 | PostgreSQL 16 + Alembic | Redis 7 (stats cache, rate limiter, triage cache) | Docker Compose | Kubernetes (Kustomize, HPA) | GitHub Actions

## Repository layout
See `backend/`, `frontend/`, `k8s/`, `load/`, `docs/`, `scripts/`, `.github/workflows/`, `compose.yaml`, `compose.prod.yaml`.

## Workflow
- `main`: stable, deployable. `dev`: integration. Work happens on short-lived branches: `feature/*`, `fix/*`, `docs/*`, `test/*`.
- Everything enters `dev` through a pull request linked to an Issue and reviewed by the other collaborator. `dev` is merged to `main` via PR when coherent.
- Conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `ci:`, `build:`.

## Team
- Abdullah-SE-bit: backend, data, AI layer, architecture
- rayyanhasan899: frontend, containers, Kubernetes, CI, documentation

Rollback procedures: [docs/ROLLBACK.md](docs/ROLLBACK.md).

AI assistance is disclosed in [docs/AI-USAGE.md](docs/AI-USAGE.md).

## License
MIT
