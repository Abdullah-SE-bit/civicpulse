# Merge conflict: `frontend/nginx.conf` (issue #23)

This was a deliberate, staged exercise. Both conflicting branches were created by the same account (`rayyanhasan899`), so it demonstrates conflict handling, not two people disagreeing.

## The two changes
Both branched from the same `dev` commit and edited the same lines of the `/assets/` block:

| Branch | PR | Commit | Change |
|---|---|---|---|
| `fix/nginx-assets-hardening` | #24 | `2ec9a55` | keeps `expires 1y` + `Cache-Control "public, immutable"`, adds `X-Content-Type-Options: nosniff` |
| `feature/nginx-assets-gzip` | #25 | `a7639a2` | adds `gzip on` + `gzip_types`, but also shortens caching to `expires 30d` + `max-age=2592000` |

## The conflict
Before opening the PRs, a trial merge (`git merge --no-commit --no-ff origin/fix/nginx-assets-hardening` on the gzip branch, then `git merge --abort`) produced this. It is the real output of that command:

```
CONFLICT (content): Merge conflict in frontend/nginx.conf
    location /assets/ {
<<<<<<< HEAD
        expires 30d;
        add_header Cache-Control "public, max-age=2592000";
        gzip on;
        gzip_types text/css application/javascript image/svg+xml;
=======
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header X-Content-Type-Options "nosniff" always;
>>>>>>> origin/fix/nginx-assets-hardening
    }
```

## What happened next (from `git log`, not from memory)
1. PR #25 (gzip) was merged into `dev` first.
2. `dev` was then merged into `fix/nginx-assets-hardening` (`de486e2`, parents `2ec9a55` and `019b5d5`). `git show --cc de486e2` shows the result: the `/assets/` block keeps the hardening branch's lines (`expires 1y`, `immutable`, `nosniff`) and **the gzip lines are gone**. A stray blank line was also left inside the block.
3. PR #24 was merged, so `dev` had immutable caching and `nosniff` but had lost gzip, i.e. the resolution discarded one side of the merge entirely.
4. PR #31 (`67bfde6`) restored the gzip lines on top, and added `text/javascript` to `gzip_types`.

Final block (current `dev`):
```
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header X-Content-Type-Options "nosniff" always;
        gzip on;
        gzip_types text/css text/javascript application/javascript image/svg+xml;
    }
```

## Why that version won
The two branches disagreed about one thing and were independent about the rest. On caching, the 1-year `immutable` policy is correct because Vite writes content-hashed filenames into `/assets/`: a changed file gets a new URL, so a long cache can never serve stale content, and shortening it to 30 days only costs repeat visitors extra requests. On `nosniff` and gzip there was no real conflict, they add independent lines, so both belong. The first resolution (`de486e2`) kept the right caching policy but dropped gzip by taking one side wholesale, which is the mistake this exercise is meant to expose: resolving a conflict means reading both sides and combining what each adds, not choosing "ours" or "theirs". The gzip loss was only noticed by re-reading the merge with `--cc`, and fixed in #31.

Not verified: nginx has not been run against this file (no Docker on the authors' machines), so neither the header nor gzip behaviour has been observed. Expected check: `curl -sI -H 'Accept-Encoding: gzip' http://localhost:8080/assets/<file>.js` should show `Content-Encoding: gzip`, `Cache-Control: public, immutable` and `X-Content-Type-Options: nosniff`.
