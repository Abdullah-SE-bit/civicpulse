# AI Usage Disclosure

Per assignment §5.5, AI assistance is disclosed here. Each entry is appended as work happens; nothing is back-filled from memory.

**Tool:** Claude Code (Anthropic), run in two separate sessions: ALPHA (GitHub account `Abdullah-SE-bit`) and BETA (GitHub account `rayyanhasan899`).

## Log

| Date | Tool / session | Area affected | Changes made by AI | Reviewed / modified by the team |
|------|----------------|---------------|--------------------|---------------------------------|
| 2026-09-24 | Claude Code / ALPHA | Repo bootstrap | Directory scaffold, .gitignore, .env.example, README, doc skeletons, LICENSE | _pending review_ |
| 2026-09-25 | Claude Code / BETA | scripts/ui_screenshots.mjs, evidence-ui workflow, docs/screenshots, docs/evidence/ui-run.md, README screenshots | Wrote the Playwright script and workflow, viewed the resulting images to check them, wrote the description from the transcript | _pending review_ |
| 2026-09-25 | Claude Code / BETA | docs/evidence/ci-gate.md, ci-red-blocked.png | Ran the red-then-green demo PR, read the run and PR status, described the user's screenshot; did not create the screenshot | _pending review_ |
| 2026-09-25 | Claude Code / BETA | scripts/evidence_rollout.sh, load/k6-rollout.js, evidence-rollout workflow, docs/evidence/rollout* | Wrote the scripts, reran the test when the first run failed, added per-failure logging, wrote up the mixed result without claiming zero downtime | _pending review_ |
| 2026-09-25 | Claude Code / BETA | k8s/base image placeholders | Replaced :latest placeholders with a non-pullable set-by-overlay tag; verified by rendering both overlays with kustomize v5.4.3 | _pending review_ |
| 2026-09-25 | Claude Code / BETA | docs/evidence/cd-run.md, README, ENGINEERING-NOTES Q2/Q3 | Read the first cd.yml run logs and artifacts and wrote up what they show; corrected statements that said cd.yml had never run | _pending review_ |
| 2026-09-25 | Claude Code / BETA | backend triage cache scope (llm.py, ollama.py, triage_service.py, tests, TRIAGE.md) | Reproduced the stale-model cache hit on merged dev, added cache_scope, two regression tests verified to fail without the fix | _pending review_ |
| 2026-09-25 | Claude Code / BETA | docs/evidence/k8s-repeat, k8s-run.md repeat section | Added the results of a repeat kind run and noted what did and did not repeat | _pending review_ |
| 2026-09-25 | Claude Code / BETA | README/RUNBOOK status, scripts/evidence_compose.sh step 8b, review of PR #46 | Reproduced the X-Forwarded-For bypass and the fix on runners before approving; added the missing through-proxy check; updated status lines | _pending review_ |
| 2026-09-25 | Claude Code / BETA | scripts/evidence_compose.sh, evidence workflow, docs/evidence/compose-* | Wrote the evidence script and workflow, read the runner transcript, tightened checks I found weak, wrote the summary from the real output | _pending review_ (results are from one CI run on a GitHub runner) |
| 2026-09-25 | Claude Code / BETA | scripts/evidence_k8s.sh, plot_hpa.py, load/k6-script.js, evidence-k8s workflow, docs/evidence/k8s* | Wrote the scripts and workflow, read the runner artifacts critically (found and fixed a weak lag definition and an HPA-status lag), wrote the summary from the real output | _pending review_ (two runs on one shared runner) |
| 2026-09-25 | Claude Code / BETA | backend/Dockerfile | Added PYTHONPATH=/app after reading the failing integration job logs | _pending review_ (confirmed only by the CI rerun) |
| 2026-09-25 | Claude Code / BETA | backend/Dockerfile, frontend/Dockerfile | Bumped base image tags and added OS package upgrades after reading the Trivy report from CI | _pending review_ (fix confirmed only by the CI rerun) |
| 2026-09-25 | Claude Code / BETA | docs/evidence/merge-conflict.md, .mailmap | Wrote the conflict write-up from git history; added a mailmap that merges duplicate author names | _pending review_ |
| 2026-09-25 | Claude Code / BETA | frontend/nginx.conf | Restored gzip lost in a merge-conflict resolution; added text/javascript to gzip_types (nginx not run locally) | _pending review_ |
| 2026-09-25 | Claude Code / BETA | README, docs/RUNBOOK.md, docs/adr/0002+0003, ENGINEERING-NOTES Q1-3,5 | Wrote from the actual code, workflows and manifests; left measurements as explicitly not done | _pending review_ (commands in the RUNBOOK have not been run) |
| 2026-09-25 | Claude Code / BETA | CI, k8s and compose defaults | Fixed the Trivy action tag, moved migrations+seed to the k8s init container, changed default triage provider to rules, removed empty-string env overrides | _pending review_ (found by reading CI logs and the backend factory/entrypoint; k8s changes not applied to a cluster) |
| 2026-09-25 | Claude Code / BETA | frontend eslint config and component tests | Added eslint, 7 component/client tests, refactored Dashboard fetch effect to fix a lint error | _pending review_ |
| 2026-09-25 | Claude Code / BETA | docs/ROLLBACK.md | Wrote the rollback runbook | _pending review_ (commands not run: no cluster available) |
| 2026-09-24 | Claude Code / BETA | k8s/ manifests, cd.yml, release.yml, scripts/kind-config.yaml, notes Q6 | Wrote Kustomize base + overlays, optional VPA, CD and release workflows | _pending review_ (YAML parse only; no cluster, kubectl or runner available) |
| 2026-09-24 | Claude Code / BETA | compose.yaml, compose.prod.yaml, notes Q7 | Wrote both Compose files and two notes paragraphs | _pending review_ (YAML parse only; not run, Docker unavailable) |
| 2026-09-24 | Claude Code / BETA | .github/workflows/ci.yml, scripts/integration.sh | Wrote CI workflow and integration script | _pending review_ (never run on a runner yet; YAML parse + bash -n only) |
| 2026-09-24 | Claude Code / BETA | Frontend (React+Vite+TS), nginx.conf, frontend Dockerfile, ADR 0001 | Wrote all frontend source, client, one validation test, Dockerfile, nginx config, ADR | _pending review_ (image build not yet run: Docker unavailable locally) |
| 2026-09-24 | Claude Code / ALPHA | Backend triage layer | Providers (rules, simulated, LLM, Ollama), factory, TriageService (retry, fallback, cache), tests | _pending review by BETA_ |
| 2026-09-25 | Claude Code / ALPHA | Backend data layer | Domain enums and state machine, models, Alembic migration, repository, ComplaintService, idempotent seed, backend Dockerfile and entrypoint, tests | _pending review by BETA_ |
| 2026-09-25 | Claude Code / ALPHA | Backend HTTP API | FastAPI app, routes, Redis stats cache + rate limiter + triage cache, health/ready/metrics, JSON logging, API tests | _pending review by BETA_ |
| 2026-09-25 | Claude Code / ALPHA | Backend audit fixes and docs | Factory/env handling fixes, k8s backend init-container change, extra Redis/config tests, TRIAGE.md, ADR 0001 (provider interface) and 0004 (PII), engineering notes 4 and 8 and index justifications. Also renamed the frontend ADR to 0002 to match the required ADR set. | _pending review by BETA_ |
| 2026-09-25 | Claude Code / ALPHA | Compose evidence on a laptop, script portability | Ran the evidence script on real Docker, found and fixed the rate-limit and cache-key defects (#46, #50), patched the script for Windows and per-run text, wrote the laptop evidence note | _pending review by BETA_ |
| 2026-09-26 | Claude Code / ALPHA | Measured evidence: triage cache, Docker context sizes, branch protection; `backend/.dockerignore` fix | Wrote the measurement script and override, ran them on real Docker, found and fixed the nested `__pycache__` ignore patterns, wrote the three evidence notes from the real output | _pending review by BETA_ |



## Rules we follow
- AI output is reviewed before merge; a line nobody can explain is not merged.
- No secrets are ever given to an AI tool or committed.
