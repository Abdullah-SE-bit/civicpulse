# UI screenshots and browser-level checks

Real screenshots taken by `scripts/ui_screenshots.mjs` (Playwright, headless Chromium, viewport 1200x800) against the Compose stack started exactly as the README quickstart does, on a GitHub runner (workflow `evidence-ui`, run [36163533189](https://github.com/Abdullah-SE-bit/civicpulse/actions/runs/36163533189)). **16 of 16 assertions passed**; the transcript is [`../screenshots/ui-transcript.txt`](../screenshots/ui-transcript.txt). Every screenshot belongs to a check on visible text, not only a picture.

Conditions: `TRIAGE_PROVIDER=rules` (deterministic keyword triage; the default `simulated` fake would give meaningless labels), seeded database (32 rows plus the one submitted during the run = 33).

| File | What it shows | Assertion behind it |
|---|---|---|
| [`01-submit-empty.png`](../screenshots/01-submit-empty.png) | Submit form | heading present |
| [`02-submit-validation.png`](../screenshots/02-submit-validation.png) | client-side validation errors on an empty submit | both field messages present |
| [`03-submit-loading-delayed-2.5s.png`](../screenshots/03-submit-loading-delayed-2.5s.png) | in-flight state: "Triaging your complaint... this can take a few seconds" | button text and disabled state |
| [`04-submit-result.png`](../screenshots/04-submit-result.png) | result card: category **water**, priority **high**, summary, provider **rules** | all four fields checked |
| [`05-dashboard.png`](../screenshots/05-dashboard.png) | paginated list, newest first, seeded Urdu-influenced complaints | row count, newest is first, "Page 1 of 2 (33 total)" |
| [`06-dashboard-filter-water.png`](../screenshots/06-dashboard-filter-water.png) | category filter | every visible row is `water` |
| [`07-dashboard-status-changed.png`](../screenshots/07-dashboard-status-changed.png) | valid transition `open -> in_progress` | select value is `in_progress` |
| [`08-dashboard-409-server-message.png`](../screenshots/08-dashboard-409-server-message.png) | invalid transition, the server's own message in red | text equals `Invalid status transition: in_progress -> open` exactly |
| [`09-stats-first-view-cache-MISS.png`](../screenshots/09-stats-first-view-cache-MISS.png) | Stats after writes: cache **MISS** | recorded by the script |
| [`10-stats-cache-hit.png`](../screenshots/10-stats-cache-hit.png) | after Refresh: cache **HIT**, category and priority counts | code element reads `HIT` |

## Honest notes
- **The loading-state screenshot is staged.** Rule-based triage answers in about a millisecond, so the script delays the POST response by 2.5 s with Playwright route interception to make the state visible. It shows the UI's behaviour while waiting, not real triage latency.
- The submitted complaint's contact field held a dummy number; the screenshot form is cleared after submit by design.
- One browser, one viewport, one run. Nothing here tests other browsers, mobile widths or accessibility tooling.
- The UI has no screenshot of the Stats view *during* a MISS with counts other than the ones shown, and no test of the error boundary or of the 429 message in the browser (both are covered by the component tests with mocked responses).
