# Rollback runbook

Production is always deployed by **immutable reference**: the commit SHA (`ghcr.io/abdullah-se-bit/civicpulse-<image>:<sha>`), set by `cd.yml` with `kustomize edit set image` on `k8s/overlays/prod`. `:latest` is pushed but never deployed. So "what is production running?" has a one-word answer: a SHA.

```bash
kubectl -n civicpulse get deploy backend frontend -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.template.spec.containers[0].image}{"\n"}{end}'
git show <sha> --stat   # exactly what that is
```

We keep two rollback mechanisms. They answer different questions.

## 1. `kubectl rollout undo`: fast, imperative (the 3 a.m. answer)

Use when users are being hurt right now and you need the previous ReplicaSet back in seconds.

```bash
kubectl -n civicpulse rollout history deployment/backend
kubectl -n civicpulse rollout undo deployment/backend            # previous revision
kubectl -n civicpulse rollout undo deployment/backend --to-revision=<n>   # a specific one
kubectl -n civicpulse rollout status deployment/backend
kubectl -n civicpulse rollout undo deployment/frontend           # only if the frontend is also bad
```

Because the Deployment uses `maxSurge: 1, maxUnavailable: 0` and the readiness probe on `/ready`, the old pods take traffic before the new ones are removed, so the undo itself is a rolling update.

Limits:
- **The cluster now differs from git.** The next push to `main` redeploys whatever `main` contains, including the bad commit if it is still there. Revert it on `main` (mechanism 2) as soon as the fire is out.
- **It does not undo database migrations.** The `migrate` init container ran `alembic upgrade head` on the way forward. Migrations must therefore stay backward compatible for one release (add columns, do not drop or rename in the same release), or the old code will run against a schema it does not understand.
- Only as deep as `revisionHistoryLimit` (default 10).

## 2. Re-apply the overlay with the previous SHA: declarative, auditable

Use once the fire is out, or when the bad change is not the latest revision. The previous SHA's images still exist in GHCR because tags are per commit.

Find the last good SHA (the last green `cd` run on `main`, or `git log main`), then either:

**a) Through git (preferred, leaves a trail and triggers CD):**
```bash
git revert <bad-sha>        # on a branch, PR into dev, then dev -> main as usual
```
`cd.yml` then tests, builds and deploys the reverted tree by its new SHA.

**b) By hand, when CD itself is the problem:**
```bash
git checkout <good-sha> -- k8s/         # manifests as they were at that commit
cd k8s/overlays/prod
kustomize edit set image \
  ghcr.io/abdullah-se-bit/civicpulse-backend=ghcr.io/abdullah-se-bit/civicpulse-backend:<good-sha> \
  ghcr.io/abdullah-se-bit/civicpulse-frontend=ghcr.io/abdullah-se-bit/civicpulse-frontend:<good-sha>
kustomize build . | kubectl apply -f -
kubectl -n civicpulse rollout status deployment/backend deployment/frontend
git checkout -- .        # do not commit the edited tag; the marker in git stays `set-by-cd`
```

The Secret is not part of the overlay, so neither mechanism touches it.

## Compose (single host)

```bash
IMAGE_TAG=<good-sha> docker compose -f compose.prod.yaml up -d
```

## When to use which

| Situation | Use |
|---|---|
| Live incident, minutes matter | `rollout undo`, then follow up with 2a |
| Bad revision is not the most recent one | 2 (choose the SHA) |
| Need a reviewable record of what changed and why | 2a |
| Cluster and git must agree afterwards | 2 |

## Evidence still to collect (not yet done)

Nothing below has been run; record real output in `docs/evidence/` when it has.
- [ ] Deploy a deliberately bad image, run `rollout undo`, capture `rollout status` and `get pods`.
- [ ] Re-apply the overlay with the previous SHA, capture `get deploy -o wide` showing the SHA.
- [ ] Zero-downtime check: run the load generator during `kubectl set image`, capture 0 failed requests.
