# Finance Tracker v2.5.1 deep test report

Date: 2 September 2026

## Result

Finance Tracker v2.5.1 passed the complete automated suite and release-package
verification. No live financial database, receipt collection, licence record or
installed application was modified during testing.

## Automated verification

- 56 tests passed, 0 failed and 0 skipped using Python 3.11.4.
- Python compilation, shell syntax and Git whitespace checks passed.
- The entire v2.5.0 regression suite remains passing.
- Five v2.5.1 tests cover native single-choice selectors; target creation and
  editing across category, period and currency; recurring-rule selectors and
  edit-state preservation; multi-account report selection; responsive mobile
  styles; and the existing Status/Settings information architecture.

## Functional and compatibility verification

- Existing target and recurring-transaction calculations remain unchanged.
- Target editing can change the selected expense category or subcategory while
  preserving validation and database uniqueness rules.
- Multi-account reporting remains a checkbox-based multi-select workflow.
- Target and recurring-rule tables use labelled responsive rows at narrow
  viewport widths, while destructive actions remain visually separated.
- The release introduces no database schema migration. Existing transactions,
  targets, recurring rules, licence values and configuration remain compatible.

Mobile behaviour was verified through automated route, markup and responsive
CSS checks at the implementation level. It was not tested on a physical iPhone
or iPad, so final on-device usability remains an operational acceptance check.

## Package verification

- Both `FinanceTracker-v2.5.1.zip` and
  `FinanceTracker-v2.5.1-macOS.pkg` were generated.
- ZIP integrity verification passed.
- The package payload contains `VERSION` 2.5.1 and 17 offline dependency wheels.
- ZIP and PKG payload scans found no database, data directory, Python cache,
  pytest cache, Git metadata, environment file, credential or token payload.
- The PKG is unsigned. macOS may therefore display the normal trust warning.

Apple Installer was not executed over `/Applications/finance_tracker`, because
that would modify the live installation. The existing v2.5.0 compatibility and
automated regression results provide the non-destructive upgrade verification;
a final on-machine Installer acceptance remains an operational deployment check.
