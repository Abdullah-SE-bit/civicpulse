# Branch protection on `main`

Read from GitHub with `gh api repos/Abdullah-SE-bit/civicpulse/branches/main/protection` on 2026-09-26; saved as [branch-protection.json](branch-protection.json) (only the settings, no URLs or tokens).

| Rule | Setting |
|---|---|
| Pull request required, approving reviews | **1** (stale approvals dismissed on new commits) |
| Required status checks | `lint-and-type`, `test-backend`, `test-frontend`, `live-services` |
| Applies to administrators | **yes** (`enforce_admins: true`) |
| Force pushes / branch deletion | not allowed |

**What this is not.** It is the API's answer, not a screenshot of the GitHub settings page; the assignment asks for a screenshot in `docs/evidence/`. A screenshot of `Settings > Branches` has to be taken from a signed-in browser. The related behaviour (a red check and a missing approval blocking a merge) is shown in [ci-gate.md](ci-gate.md).

**Known gap.** The very first commit (LICENSE, `.gitignore`, README stub) was pushed straight to `main` because a repository needs a base commit before a pull request can target it; every later change went through a pull request.
