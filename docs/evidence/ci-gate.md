# CI gate: a red check blocks the merge, then it goes green

Demo PR [#67](https://github.com/Abdullah-SE-bit/civicpulse/pull/67) (`test/ci-gate-demo` into `main`, never merged). Its first commit adds a test that fails on purpose (`frontend/tests/ci-gate-demo.test.ts`, `expect(1 + 1).toBe(3)`); the second removes it.

## Red
CI run [36124880264](https://github.com/Abdullah-SE-bit/civicpulse/actions/runs/36124880264): `test-frontend` **failed**; `build` and `integration` were **skipped** because they depend on it (`needs:`); lint and types, backend tests, manifests and `backend-live / live-services` passed.

Screenshot of the merge box on the PR: [`ci-red-blocked.png`](ci-red-blocked.png). It shows "1 failing, 2 skipped, 5 successful checks", `ci / test-frontend` failing and marked **Required**, `backend-live / live-services` and `ci / lint-and-type` marked **Required**, and "Merging is blocked: at least 1 approving review is required".

## Green
The fix commit `a0f7b30` removed the test. CI run [36125919459](https://github.com/Abdullah-SE-bit/civicpulse/actions/runs/36125919459): every job succeeded (`changes`, `lint-and-type`, `test-backend`, `test-frontend`, `manifests`, `build (backend)`, `build (frontend)`, `integration`). Screenshot of the green merge box: **not yet added**.

## What this does and does not show
- The **Required** badges show the checks above are configured as required status checks on `main`, and the merge box shows the approval requirement. Together they are the gate.
- After the checks went green, the API still reported `mergeStateStatus=BLOCKED`, `reviewDecision=REVIEW_REQUIRED`: the remaining blocker is the required approval, which the PR's own author cannot supply. So "blocked" in the red state has two causes at once (a failing required check and the missing approval); the screenshot lists both, the API status alone could not separate them.
- Nothing was merged, and no merge was attempted, so this shows the gate's *display and status*, not a refused `merge` call.
