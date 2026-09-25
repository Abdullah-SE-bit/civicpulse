# First CD run (`cd.yml` on `main`)

Workflow `cd`, run [36102402634](https://github.com/Abdullah-SE-bit/civicpulse/actions/runs/36102402634), triggered by the merge of PR #56 (`dev` into `main`, commit `3846128`, full SHA `38461280c7a696636f8f2f4935ba5ad62473c317`). All three jobs succeeded, in order, gated by `needs:`.

| Job | Result | What the log and artifacts show |
|---|---|---|
| `test` | success | backend (ruff, mypy, pytest with coverage gate) and frontend (tsc, tests) on the merged result |
| `build-push` | success | both images built and pushed to GHCR tagged with the commit SHA and `latest`; manifest digests were emitted (`sha256:f98703df...`, `sha256:1a1fbfbe...`); SBOMs generated with Syft and kept as workflow artifacts: `sbom-backend.spdx.json` (391 KB) and `sbom-frontend.spdx.json` (118 KB) |
| `deploy-k8s` | success | kind cluster in the runner, ingress-nginx and metrics-server installed, the two SHA-tagged images pulled from GHCR and loaded into kind, `k8s/overlays/prod` applied with the SHA, `kubectl rollout status` succeeded for postgres, redis, backend and frontend, smoke test through the Ingress created a complaint and read it back (`category` returned `"streetlights"`), then `kubectl get hpa` was printed |

## Deployed by SHA
The final "What is running" step lists the Deployments' images:
`ghcr.io/abdullah-se-bit/civicpulse-backend:38461280c7a696636f8f2f4935ba5ad62473c317` and `...civicpulse-frontend:38461280c7a696636f8f2f4935ba5ad62473c317`, 2/2 replicas each. No `latest` was deployed.

## Details worth knowing
- The HPA line printed at the end reads `cpu: <unknown>/60%` because it was captured about 54 s after apply, before metrics-server had data. That is a timing artefact of where the step sits, not a scaling result; nothing about HPA behaviour is claimed from this run (see `k8s-run.md` for measured behaviour).
- The cluster is ephemeral and destroyed with the runner, so this run shows that the published images and the prod overlay work together, not that anything stays deployed anywhere.
- Secrets: the Secret was created in the job from generated values and an optional `LLM_API_KEY` repository secret; no secret value is in the repository.

## Not verified from here
- **GHCR package visibility and the tag list.** The token available to the author lacks `read:packages`, so the packages could not be listed. Whoever owns the repository should open the two packages under the repository's Packages page, confirm the SHA tags are there, and make them public if the submission needs public links.
- `release.yml` (tag `v*`) has not run.
- No rollback (`kubectl rollout undo` or re-applying an earlier SHA) has been exercised against this deployment.
