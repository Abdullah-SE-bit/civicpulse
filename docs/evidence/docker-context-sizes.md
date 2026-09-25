# Docker build-context sizes, with and without `.dockerignore`

**Method.** For each build context, a probe Dockerfile (`FROM scratch` + `COPY . /ctx`) is built once with the real `.dockerignore` and once with it temporarily moved aside; the size of the resulting image is exactly the bytes that got through the ignore filter. (BuildKit's own `transferring context` lines are lazy and reported 917 bytes for a 217 kB directory, so they were not used.) Docker 29.8.0 on Windows 11. Two trees: a **clean** copy from `git archive` of `dev` (what a fresh clone sends), and this laptop's **working tree** (which has `backend/.venv` at 183 MB and caches from local runs).

| Context | With `.dockerignore` | Without |
|---|---|---|
| backend, clean clone | 204.0 kB | 279.0 kB |
| backend, working tree, **before** the pattern fix below | 486.5 kB | 269.7 MB |
| backend, working tree, **after** the pattern fix | **204.4 kB** | 269.7 MB |
| frontend, clean clone | 293.5 kB | 315.8 kB |
| frontend, working tree | 293.5 kB | 315.9 kB |

## What the numbers say
- On a fresh clone the ignore files remove little (75 kB backend, 22 kB frontend: mostly `tests/`), because a fresh clone has no `.venv`, `node_modules` or caches to send. The real protection is on a developer machine: without `backend/.dockerignore` this laptop would send **269.7 MB** (mostly `.venv`) into every backend build; with it, 204 kB.
- The frontend row for the working tree does **not** include `node_modules`: none exists in this worktree, so its "without" figure understates what a machine that has run `npm ci` would send. That case was not measured.

## A defect this measurement found
Before the fix, the backend working-tree context was **486.5 kB** instead of 204 kB. `__pycache__/` and `*.pyc` in a `.dockerignore` only match at the context root; the compiled files live in `app/__pycache__/` etc., so about 280 kB of local `.pyc` files were still sent (429 kB of `.pyc` in the tree). Changing them to `**/__pycache__` and `**/*.pyc` brought the working-tree context back to 204.4 kB, equal to the clean clone. CI was never affected (fresh checkouts contain no `.pyc`); local builds were.
