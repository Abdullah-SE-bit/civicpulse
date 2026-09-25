# Compose evidence run: Windows laptop

The same `scripts/evidence_compose.sh` as [compose-run.md](compose-run.md), run on a development laptop instead of a GitHub runner, against `dev` at `b125137` (which includes the rate-limit and triage-cache fixes). Result: **48 PASS, 0 FAIL**. Raw output: [compose-laptop-transcript.txt](compose-laptop-transcript.txt) (hostname redacted, nothing else edited).

**Conditions.** Windows 11 Pro, Git Bash, Docker 29.8.0 (Docker Desktop, containerd image store), Docker Compose v5.5.1, 12 CPUs, 7.6 GB memory given to Docker, images built locally.

## What running it here found
1. **Windows separator.** `COMPOSE_FILE=a:b` is invalid on Windows (`;` is the default separator), so every `docker compose` call failed and 10 checks failed; several *negative* checks passed falsely while `docker compose` was broken. Fixed with `COMPOSE_PATH_SEPARATOR=:`.
2. **Rate-limit bypass through nginx** (issue #45, fixed in #46): 30 of 30 POSTs succeeded with a rotating spoofed `X-Forwarded-For`; after the fix 20 x 201 then 10 x 429.
3. **Triage cache ignored the provider** (issue #49, fixed in #50): a result cached by `simulated` was served after switching to another provider. The script now uses a unique text per run so a rerun on a dirty Redis volume tests what it claims.

## Numbers that differ from the runner
Image sizes as reported by `docker image ls` on this machine: backend **298 MB**, frontend **92.9 MB** (runner: 194 MB and 60.1 MB). Both are real measurements. `docker history` shows the frontend's layers on this machine: nginx base about 38.7 MB, plus a 13.5 MB `apk upgrade` layer added by the base-image CVE fix (#37), plus 184 kB of app files. Why the runner's figure is smaller is **not established** (different Docker version and image store; the runner run may also predate #37). Nothing here proves the frontend contains Node: check 4 asserts `node` and `node_modules` are absent.

## Not covered
Kubernetes, HPA/VPA and load tests were not run on this laptop; see `k8s-run.md` for the runner-based evidence. The default `simulated` provider was used except in the provider-failure step.
