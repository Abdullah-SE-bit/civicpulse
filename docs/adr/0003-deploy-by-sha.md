# ADR 0003: Deploy images by commit SHA, never `:latest`

Status: accepted (digest pinning and signing not implemented)

## Context
"What is production running?" must have a one-word answer that can be pasted into `git show`. A mutable tag cannot give that: `:latest` moves under a running deployment, and a pod that restarts can silently pull a different image than its siblings.

## Decision
- CD (`.github/workflows/cd.yml`, on push to `main`) builds both images and pushes each as `:<github.sha>` and `:latest`. `:latest` exists for humans only.
- The deploy job sets the prod overlay to the SHA with `kustomize edit set image` in the runner and applies it (`cd.yml`, "Apply overlays/prod pinned to the commit SHA"). The committed overlay carries the marker `set-by-cd` (`k8s/overlays/prod/kustomization.yaml:7-8`), so a plain `kubectl apply -k` of the committed file cannot deploy `latest`; it deploys an image that does not exist and fails visibly.
- Publishing and deploying jobs are gated with `needs:` (`build-push` needs `test`; `deploy-k8s` needs `build-push`). Push permission is `packages: write` on the `GITHUB_TOKEN`, scoped to that job only.
- Rollback is the same mechanism pointed at an older SHA (`docs/ROLLBACK.md`).

## Alternatives
- Deploy by image digest (`@sha256:...`): immutable even if someone re-pushes a tag. The digests are already emitted as job outputs; using them for the deploy, plus Cosign signing and verification, is the next step and is not done.
- Semver tags only: release workflow does this for `v*` tags, but every merge to `main` would need a version bump.

## Consequences
- Every deployment is traceable to one commit; rollback is an audit-able one-line change.
- A tag can still be overwritten by anyone with write access to the package, so SHA tags are immutable by convention only.
- kind in the CD runner is ephemeral, so this pipeline proves that the manifests and images work together; it does not run a long-lived environment.
