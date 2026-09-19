# Finance Tracker v2.9.0 validation

Validation date: 19 September 2026. Baseline: GitHub v2.8.0 / main at `b405ffb85f3271c25d647d461674e35b731c69f5`.

## Automated tests

`.venv/bin/python -m pytest -q --tb=short`: **233 passed, 0 failed, 0 skipped**.

The full 204-test v2.8 suite remains in place. The 29 new tests cover independent classification and unknown defaults, capital/prize exclusions, normal rent funded from capital, history maturity, current asset/net-worth reconciliation, FX sensitivity, funding transitions and exhausted source skipping, strategy end dates stopping forecasts and postings, pension gross/net/cumulative monitoring, capital-ledger reconciliation, inheritance through Pending, read-only scenarios, account-scoped JSON, estimated forecast residuals, authenticated/Read Only/CSRF behavior, configuration validation and rollback.

Migration tests verify repeated migration, preservation of renamed funding sources and rollback on a forced schema-version write failure. Test fixtures exclude release binaries and Git metadata from isolated copies; application data is never copied into test application directories.

## Representative migration

Used SQLite's read-only backup API to copy the workspace database. Prepared the v2.8 schema, captured every original column/row in accounts, transactions, categories, users, recurring rules/occurrences, Pending, category targets, settings, CSV import batches, valuations and FX rates, then applied v2.9 twice. All original values were preserved except schema_version. Integrity check returned `ok` and foreign_key_check returned no violations. The original database hash was unchanged.

## Browser and export regression

**150 page/engine/viewport combinations passed**, with zero JavaScript errors and no document-level horizontal overflow. Engines: installed Google Chrome and Playwright WebKit 26.5. Viewports: desktop 1440×1000, iPad 820×1180 and iPhone 390×844. Mobile contexts enable touch/mobile behavior.

Coverage includes Dashboard, Accounts, Transactions, Pending, Recurring/editor/report, category reports, Upcoming, Scheduled Forecast, Search, CSV Import, Financial Review, Targets, Quick Entry, Transfer, Settings, Status, Financial Health, classification views, funding configuration and Estimated Forecast. Expanded funding configuration and Financial Health were visually inspected on mobile/tablet. Detailed Financial Health panels default collapsed to keep mobile navigation manageable.

**42 scenario/export lifecycle checks passed**: preset change/reset, native-share success/cancellation/error (simulated), actual JSON blob download with schema validation, HTTP export error and timeout; navigation to Accounts remained operational afterward in every engine/device context. The test harness is `tests/browser_v290.cjs` and requires an isolated synthetic localhost fixture, `FINANCE_TEST_URL`, and a Playwright runtime with WebKit plus Chrome. It refuses non-localhost targets.

Physical iPad/iPhone hardware, native share-sheet implementation and installed-PWA behavior were not directly tested. Native sharing was mocked to exercise each return path; WebKit provided browser-engine and responsive-layout coverage. This is not a claim of physical-device validation.

## Installer and artifacts

Built the macOS package with the existing offline wheelhouse and expanded it. Application modules, templates, static assets and tests matched source; VERSION was 2.9.0. No financial databases, receipts, secrets, virtual environments, Git metadata, caches or nested release binaries were present.

Ran the packaged preinstall/postinstall scripts against an isolated installation created from tag v2.8.0. The pre-upgrade database backup matched its source byte-for-byte. Data, authentication/Tailnet settings, secret key, synthetic receipt and virtual-environment marker survived. Offline dependency installation succeeded; the upgraded application imported under its installed virtual environment and passed version, integrity and foreign-key checks. Operating-system service commands and curl were stubbed; this was not a live installation.

Final artifacts are rebuilt from committed source. Release asset SHA-256 digests are provided separately. The GitHub release contains the matching installer, source ZIP, update notes, validation report and checksum file.

## Operational limits

No live deployment or production-data migration was performed. No live Dropbox upload, external Tailnet connectivity test or real LaunchAgent restart occurred. Existing auth, Tailnet guards, backups, deletion failure handling, CSV and PDF/print/share routing remain covered by the regression suite. New calculations use existing FX data and make their historical/projection assumptions visible. The installer remains unsigned and uses the existing platform-specific offline wheelhouse.
