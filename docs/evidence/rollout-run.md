# Rolling update under load, and both rollback mechanisms

Real output of `scripts/evidence_rollout.sh` on a kind cluster inside a GitHub runner (workflow `evidence-rollout`, `.github/workflows/evidence-rollout.yml`). k6 sends **25 req/s for 300 s** (`load/k6-rollout.js`, `GET /api/complaints?page=1&page_size=20`) through the Ingress while the script runs, in order: `kubectl set image` roll-forward, `kubectl rollout undo`, then the overlay re-applied pinned to a new tag and then back to the old one.

**Two limits of what this shows.** The "new" image is the *same image re-tagged* (`dev` and `dev-v2`), so this measures rollout mechanics, not a code change. And there was no metrics-server, so the HPA could not change replica counts during the test (2 replicas throughout); the cluster, ingress and k6 share one 4-vCPU runner.

Backend Deployment under test (from the manifests): `maxSurge: 1`, `maxUnavailable: 0`, `terminationGracePeriodSeconds: 30`, `preStop: sleep 10`, readiness on `/ready`.

## Rollback mechanisms (worked in every run)
| Step | Result |
|---|---|
| `kubectl set image deployment/backend backend=...:dev-v2` | rollout complete about 13 s later, Deployment image `:dev-v2` |
| `kubectl rollout undo deployment/backend` | rollout complete about 13 s later, image back to `:dev` (`rollout history` shows the revisions) |
| overlay re-applied with `kustomize edit set image ...:dev-v2` then `kustomize build . \| kubectl apply -f -` | image `:dev-v2` |
| same with the previous tag `:dev` | image `:dev` again |

Both documented mechanisms in `docs/ROLLBACK.md` therefore work as written on kind, using image **tags** (`dev`, `dev-v2`), not commit SHAs (SHA-tagged images were exercised by `cd.yml`, see `cd-run.md`, but not rolled back).

## Failed requests during the rollouts: mixed result
| Run | requests | failed | notes |
|---|---|---|---|
| 36104314694 | 7501 | **30 (0.39%)** | the first run; the script did not yet record per-failure details, so **cause unknown**; latency otherwise normal (p95 about 7 ms, max 106 ms) |
| 36104959436 (attempts 1 and 2), 36105679762, 36105686524, 36105691982 | about 7,500 each | **0** | detailed logging on: 0 non-200 responses in every phase; p95 5-9 ms |

So five later runs (about 37,500 requests) saw no failures, and one run saw 30 that the data cannot explain. The failure rows and ingress logs that would have located them were not captured in that first run. The four checks pass in every run; the fifth ("zero failed requests") failed once and passed in the others.

What can honestly be said: the configuration (`maxUnavailable: 0`, readiness gate, 10 s `preStop`) held zero-failure rollouts in most runs, but **not in all**, and "zero downtime" is not established. One plausible cause is that the run started load immediately after the initial deployment while the cluster was still settling, but that is a guess, not something these runs show.

Files: [`rollout/clean-run/`](rollout/clean-run/) (transcript and k6 summary of a passing run) and [`rollout/run-with-30-failures/`](rollout/run-with-30-failures/) (the run with failures).
