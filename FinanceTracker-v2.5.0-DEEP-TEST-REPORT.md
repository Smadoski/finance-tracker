# Finance Tracker v2.5.0 deep test report

Date: 2 September 2026

## Result

Finance Tracker v2.5.0 passed the complete automated suite and isolated package
verification. No live financial database, receipt collection, licence record or
installed application was modified during testing.

## Automated verification

- 51 tests passed, 0 failed and 0 skipped using Python 3.11.4.
- Python compilation, shell syntax and Git whitespace checks passed.
- The entire pre-existing v2.4.7 regression suite remains passing.
- New tests cover recurrence frequencies; 31st/month-end and leap-year handling;
  exact, previous and next working-day rules; pause, skip and end dates; catch-up
  and duplicate prevention; automatic and pending posting; linked transfers;
  all four target periods; parent/subcategory actual aggregation; double-count
  protection; under, exact and over target states; existing currency conversion;
  Read Only restrictions; Status/Settings rendering; and repeatable migration.

## Upgrade and data verification

- A representative v2.4.7 database copy migrated twice without error.
- Existing transactions, `Licensed To` and `Licence Number` values remained
  unchanged.
- The migration created `recurring_rules`, `recurring_occurrences` and
  `category_targets` and retained database-level occurrence uniqueness.
- The migration and all tests used temporary copies, never the live database.

## Application workflow verification

From the extracted final package payload in a temporary directory:

- application import and database startup passed;
- a live Waitress HTTP health check passed on isolated loopback port 18080;
- Dashboard, Status, Settings, Recurring and Target Report pages rendered;
- Quick Entry created the expected pending expense;
- a normal transfer created exactly two linked legs;
- local backup created a readable database copy;
- recurring processing and target reporting passed through automated tests.

Dropbox network upload and Tailnet/Tailscale connectivity were not exercised,
because they require the live machine's credentials and network configuration.
Their existing regression coverage remains passing and their implementation was
not replaced by v2.5.0.

## Package verification

- Both `FinanceTracker-v2.5.0.zip` and
  `FinanceTracker-v2.5.0-macOS.pkg` were generated.
- The package payload contains `VERSION` 2.5.0 and 17 offline dependency wheels.
- All requirements installed from that wheelhouse with network access disabled,
  and Flask, ReportLab, Waitress and Vision imported successfully.
- ZIP and PKG payload scans found no databases, data directory, Python caches,
  pytest caches, Git metadata, environment files, credentials or tokens.
- The PKG is unsigned. macOS may therefore display the normal trust warning.

Apple Installer was not executed over `/Applications/finance_tracker`, because
that would modify the live installation. Upgrade behaviour was instead verified
using the representative v2.4.7 fixture and extracted package payload. A final
on-machine Installer acceptance remains an operational deployment check.

