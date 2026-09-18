# Finance Tracker v2.7.0 validation

Validation date: 9 September 2026. Baseline: v2.6.1.

## Automated results

`.venv/bin/python -m pytest -q --tb=short`: **147 passed, 0 failed, 0 skipped** (13.37 seconds).

The complete pre-existing suite ran alongside v2.7 service and HTTP coverage. Coverage includes target actuals and child aggregation; scheduled commitments; holiday/weekend adjustments; occurrence deduplication; 30/60/90-day multi-currency forecasts and transfer legs; no balance mutation; combined search filters; CSV preview/mapping/duplicate review/import/replay rejection; invalid rows; AI JSON calculated values and secret-field exclusion; historical trends; read-only import enforcement; repeatable migrations; existing Quick Entry, transfer, recurring, target, settings and status paths.

A real isolated SQLite backup was opened and passed integrity checking with the fixture transaction preserved. Dropbox connection, upload and retry behaviour was exercised through the application functions with a mocked remote adapter. No real Dropbox account was contacted and no credentials were accessed.

## Upgrade and startup

A read-only SQLite backup of the workspace's representative database was migrated twice. Accounts, transactions, categories, targets, recurring rules, recurring audit records and Pending records were compared before/after; existing financial data was unchanged. The added calendar field defaults to weekdays-only. SQLite integrity check returned `ok`. The original database was not migrated or written by validation.

The application started from an isolated source copy and synthetic database with the recurring scheduler disabled. Existing installation scripts were inspected: they preserve the data directory and existing security settings, install offline wheels, and check the local service after installation. The built package was expanded and its payload inspected. A production installer upgrade was not run.

## Browser verification

Headless Google Chrome checked **36 page/viewport combinations**, all HTTP 200 and without document-level horizontal overflow. Dimensions: desktop 1440×1000, iPad 820×1180, iPhone 390×844.

Pages: Dashboard, Targets, Recurring, Upcoming, Forecast, Search, CSV Import, AI Financial Review, Quick Entry, Transfer, Settings and Status. Mobile navigation opened and the Forecast link was visible. Dashboard, target and forecast screenshots were captured; final desktop target and iPhone dashboard layouts were visually inspected, including the enlarged visible logo. These were simulated viewports, not physical iPhone/iPad tests. CSV review/import and JSON/CSV exports were also exercised through HTTP/service tests.

## Release artifacts

- `FinanceTracker-v2.7.0.zip`: source release.
- `FinanceTracker-v2.7.0-macOS.pkg`: installer built using the existing local wheelhouse.
- `UPDATE-v2.7.0.md`: changes, methods and migration/rollback notes.
- `HOLIDAY-CALENDARS.md`: calendar scope and official reference links.

Version is 2.7.0 in VERSION, application footer, current README heading and release manifest. Previous release notes retain their historical version numbers. Generated package payload excludes financial databases, receipts, secrets, virtual environments, Git metadata and caches. Credential-pattern scanning found no embedded credentials. Synthetic tests contain deliberately fake credential markers.

## Limits

No live deployment, real Dropbox upload, physical-device test or external Tailscale connectivity test was performed. Installer is unsigned and uses the existing offline wheelhouse; its platform-specific wheels must match the target Python environment. Forecasts include scheduled activity only. UK calendar means England/Wales; future exceptional bank closures require calendar maintenance. See release notes for projection and history assumptions.
