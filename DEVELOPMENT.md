# Current baseline and development status

Verified 2026-09-27:

- Repository: https://github.com/Smadoski/finance-tracker
- Checkout at audit: main, clean; HEAD and local origin/main were
  `8da294e13fbdc8dabd9741de5469a90a09dfbd26`.
- Remote main and peeled annotated tag v2.9.0 resolve to that same commit.
- GitHub lists v2.9.0 as latest, published 2026-09-19T07:38:47Z, neither draft nor
  prerelease. [Published release](https://github.com/Smadoski/finance-tracker/releases/tag/v2.9.0).
- VERSION and README say 2.9.0; app.py and both installer/archive builders read
  VERSION. No current version marker needs changing. The app's legacy missing-file
  fallback is 2.1.0; it is not evidence of the current release.
- User reports running v2.9, consistent with repository v2.9.0. The live installation
  was not inspected; asset digests and deployment were not reverified in this audit.

## Current work

Prepared v2.10.0 release, based on the verified v2.9.0 commit above. VERSION,
README and package metadata now use 2.10.0. The database schema marker remains
2.9.0 because no schema change is required. Historical version notes above describe
the baseline at the audit, not the current candidate version.

Branch: `codex/release-v2.10.0`. Home redesign, credit-card ledger, conversion,
refund handling and forecasts are implemented. See UPDATE-v2.10.0.md and
FinanceTracker-v2.10.0-TEST-REPORT.md for behaviour, verification and limits.

The release is prepared for review, not merged, tagged, published or installed.
GitHub's latest published release remains v2.9.0. Do not infer deployment from a
local installer or VERSION. The user's last reported installed baseline is v2.9.

Read [ROADMAP.md](ROADMAP.md) for implemented versus outstanding scope,
[CHANGELOG.md](CHANGELOG.md) for release history, and
[RELEASE-WORKFLOW.md](RELEASE-WORKFLOW.md) for promotion requirements. This file
is the development/status record; no separate BUILD.md is needed.

## Start and finish each task

1. Read AGENTS.md and the records above. Inspect status, branch, HEAD, VERSION,
   remote main, peeled release tag and GitHub Releases. If offline, label remote
   evidence unavailable; do not present cached refs as current verification.
2. State the verified baseline and intended scope. Reconcile requests with code
   and tests before adding them to the roadmap. Use a codex/ branch for changes.
3. Preserve user changes and live data. Verify using isolated fixtures/copies.
4. Update roadmap/status and Unreleased changelog with the same change. Record
   checks actually run and remaining device/deployment limits. Do not upgrade a
   historical test report into a claim about the current work.
5. At release, synchronise VERSION and current documentation, then follow the
   existing release workflow. Keep historical notes intact.

## Audit validation

Source inspection and fresh GitHub release/remote-reference checks establish the
baseline above. Fresh focused regression run: `.venv/bin/python -m pytest -q --tb=short
-p no:cacheprovider tests/test_v280_release.py` — **57 passed in 2.04s**, using
isolated fixtures. Documentation diff whitespace and local Markdown links checked. Historical v2.9 validation reports 233 automated passes;
that is the release record, not a fresh full-suite run in this documentation task.

# Finance Tracker development

Historical origin: this working copy was created from `FinanceTracker-v2.4.6.zip`.
That archive is provenance only, not the development baseline.

## Run

```sh
./dev-start.sh
```

Open <http://127.0.0.1:8080>. Development data is written to `data/` inside
this working copy and is intentionally excluded from Git.

## Test

```sh
source .venv/bin/activate
pytest
```

The development launcher listens only on this Mac. Use the release service
scripts only when intentionally testing LAN or production deployment.


## Browser verification

Run `.venv/bin/python tests/serve_browser_fixture.py` to create a disposable copy
with synthetic data and serve it on localhost port 18210. With Playwright/Chrome
available, set `FINANCE_TEST_URL=http://127.0.0.1:18210` and run
`node tests/browser_v2100.cjs` and `node tests/browser_v290.cjs`. These cover new
Home/card pages and retained Financial Health/JSON flows respectively. The fixture
never serves the working database. Stop it after verification.
