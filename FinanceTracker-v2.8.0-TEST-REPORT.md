# Finance Tracker v2.8.0 validation

Validation date: 18 September 2026. Baseline: original released v2.7.0, recovered from the preserved 9 September source ZIP and recorded as `b8be5eb` / tag `v2.7.0`.

## Automated tests

Command: `.venv/bin/python -m pytest -q --tb=short`

| Collected | Passed | Failed | Skipped |
| --- | --- | --- | --- |
| 204 | 204 | 0 | 0 |

Duration: 19.80 seconds on the local Python 3.14 environment. The recovered baseline was tested independently: 147 passed. The combined release includes all 147 planning/regression tests, 51 deletion/PDF/recurring-report tests from the focused fixes work, and 6 additional integration/migration tests. The version assertion now expects 2.8.0; historical test names and explicit historical export-version fixtures remain unchanged.

The additional integration tests verify that new frequencies retain holiday calendars, that report payment dates agree with Upcoming, that scheduled forecast expenditure agrees with target projections, and that the original v2.7 recurring schema migrates with its calendar column, occurrence links, indexes and AUTOINCREMENT state intact. The full suite also verifies Read Only and authenticated/Tailnet export restrictions.

## Migration validation

Used SQLite's read-only backup API to copy the existing workspace database into a temporary location. Applied the existing v2.7 migration, then the new v2.8 migration twice. Compared all rows in accounts, transactions, categories, recurring rules, recurring occurrences, Pending, targets, CSV-review storage and settings. Values were unchanged except schema_version. Integrity check and quick check returned `ok`; foreign_key_check returned no violations. The original database hash was unchanged. No production database was opened by a test application or migrated.

The frequency-constraint rebuild has an explicit rollback regression. Existing v2.7 calendar choices survive; foreign-key enforcement is restored. The superseded fixes-only schema is recognised without a second rebuild, while the preceding additive migration supplies any missing planning/calendar tables and columns.

## Installer upgrade rehearsals

Built `FinanceTracker-v2.8.0-macOS.pkg` using the established build script and existing offline wheelhouse. Expanded package scripts were run against isolated installations created from v2.6.1 (`e56aa38`) and original v2.7.0 (`b8be5eb`). Both passed:

- pre-upgrade database backup creation and byte comparison;
- data, authentication/Tailnet settings, .secret_key, receipt and .venv marker preservation;
- offline dependency installation into the isolated virtual environment;
- upgraded application import, 2.8.0 version, SQLite integrity and foreign-key checks.

Console-user discovery, LaunchAgent commands and installer HTTP health commands were stubbed to keep this rehearsal isolated. This is not a native macOS Installer, live LaunchAgent restart or production upgrade test. Installer and service scripts remain unchanged.

## Browser and exports

Headless installed Chrome, synthetic localhost application. Viewports: desktop 1440×1000, iPad 820×1180, iPhone 390×844.

51 page/viewport checks passed: all HTTP 200, no document-level horizontal overflow and no JavaScript errors. Checked Dashboard, account page, recurring list/editor, category report, recurring report with/without equivalents, Upcoming, Forecast, Search, CSV Import, AI Financial Review, Targets, Quick Entry, Transfer, Settings and Status. Report frequency filtering, reset, defaults and expanded-filter layout were exercised at each size. EUR 108.33/month equivalent was checked for a EUR 100 four-weekly payment. Mobile Dashboard and recurring-report screenshots were visually inspected.

Account and recurring PDFs, filtered recurring CSV and AI Financial Review JSON were retrieved successfully with expected MIME types; AI metadata reports 2.8.0. Both recurring PDF pages were rendered with Poppler and visually inspected. Inline/download behavior and optional equivalent columns are covered by automated tests.

## Release integrity and publication

The original v2.7.0 source ZIP is retained unchanged. Its tag records the recovered release; its original installer had been overwritten by the mistakenly numbered fixes-only package, which is not presented as an original v2.7 artifact.

The v2.8 release uses matching committed source, VERSION, installer metadata, release notes and source archive. Package/source-archive checks exclude financial databases, receipts, secrets, virtual environments, Git metadata, Python/pytest caches and old ZIP/PKG outputs. Published artifacts include SHA-256 checksums. See RELEASE-WORKFLOW.md for the source/tag/assets publication checklist introduced to prevent local-only releases.

## Limits

Physical iPhone/iPad testing, Safari/native Share Sheet, physical print output, live Installer/LaunchAgent restart and external Tailscale access were not performed. The installer is unsigned and retains the existing offline wheelhouse: platform-specific wheels must match the target Python/macOS environment. No live deployment or production-data/configuration modification was performed.
