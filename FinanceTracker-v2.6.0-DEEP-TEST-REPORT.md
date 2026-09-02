# Finance Tracker v2.6.0 deep test report

Date: 2 September 2026

## Result

Finance Tracker v2.6.0 passed the complete automated suite and responsive
acceptance review. No live financial database, receipt collection, licence
record or installed application was modified during testing.

## Automated verification

- 60 tests passed, 0 failed and 0 skipped using Python 3.11.4.
- Python compilation, shell syntax and Git whitespace checks passed.
- The complete v2.5.1 regression suite remains passing.
- Four new UI contract tests cover shared disclosure components, collapsed
  creation forms, immediate Quick Entry access, compact filters, grouped
  Settings, responsive navigation and Status/Settings information ownership.

## Responsive acceptance review

Fifteen major routes were inspected in the live local application at desktop
(1440px), iPad landscape (1024px), iPad portrait (768px), iPhone landscape
(844px) and iPhone portrait (390px): 75 route/viewport combinations in total.

- No unintended horizontal page scrolling was detected.
- No interactive controls extended beyond the viewport.
- Categories, Recurring Transactions and Settings received additional visual
  screenshot inspection at mobile/tablet widths.
- New-item forms, report filters, management controls and settings groups expose
  clear native open/closed states with keyboard-accessible focus treatment.

This was browser viewport testing, not physical-device testing. The release was
not tested on a physical iPhone or iPad.

## Compatibility

- No database migration or financial-core change is included.
- Existing transaction, transfer, recurrence, target, report, backup, Dropbox,
  authentication, role and licence behavior remains covered by regression tests.
- The application started successfully against the existing development data.
- Existing v2.5.1 databases and configuration remain directly compatible because
  v2.6.0 makes no schema change.

## Package verification

- Both `FinanceTracker-v2.6.0.zip` and
  `FinanceTracker-v2.6.0-macOS.pkg` were generated.
- ZIP integrity and release payload scans passed.
- The package contains the offline dependency wheelhouse.
- ZIP and PKG payload scans found no database, data directory, Python cache,
  pytest cache, Git metadata, environment file, credential or token payload.
- The PKG is unsigned. macOS may therefore display the normal trust warning.

Apple Installer was not executed over `/Applications/finance_tracker`, because
that would modify the live installation. Final on-machine Installer acceptance
remains an operational deployment check.
