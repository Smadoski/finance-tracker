# Finance Tracker v2.8.0

## Baseline and retained functionality

This release is built on the original released v2.7.0 planning application recovered byte-for-byte from `FinanceTracker-v2.7.0.zip` dated 9 September 2026. Its source is now recorded under Git tag `v2.7.0`. All planning dashboards, targets/projections, Upcoming, Forecast, search, CSV import/export, AI Financial Review, holiday calendars and responsive UI remain included.

The earlier local fixes-only package incorrectly labelled v2.7.0 is superseded by v2.8.0. It was based on v2.6.1 and omitted the planning additions; it is not published as the original v2.7.0 release.

## Fixes and additions

- Transaction deletion now releases the recurring occurrence's foreign-key reference within the same transaction as deletion. Audit history stays posted, preventing the deleted occurrence from being posted again. Linked transfer legs are deleted together; unrelated transactions and shared receipts are preserved. Database failures roll back completely.
- Account, net-worth and category statements have separate View, Download/Save, Print and Share/Export actions. Native inline PDF viewing uses the existing authenticated connection. On Mac use the PDF viewer Print control or Cmd+P; on iPhone/iPad use Share → Print or Save to Files. Category PDF actions use the current form selections. No authentication or Tailnet settings are relaxed.
- Recurring schedules add Every 4 weeks (exactly 28 days), First day of month, Last day of month, Fortnightly and Six-monthly. Existing schedules retain their meaning. Month-end dates handle leap years; holiday/working-day adjustments remain separate from nominal dates.
- Reports → Recurring Transactions Report (also linked from Recurring) combines category, account, currency, frequency and active/inactive filters, with a reset action.
- Monthly/annual equivalents are optional and off by default. Original payment amounts and frequencies stay visible. Decimal normalisation gives €100 every four weeks = €1,300 annually = €108.33/month equivalent. Daily/weekly/fortnightly use 365/52/26 payments per year; monthly/month-boundary, quarterly, six-monthly and annual use 12/4/2/1. These are normalised costs, not counts in a particular calendar year.
- Frequency totals are separated by currency and transaction type. Overall equivalents reuse the existing exchange rate and conversion directions, preserving Decimal arithmetic for this report. Income and transfers remain separate from expenditure. Inactive rows contribute only when included by the selected filters.
- PDF and numeric CSV exports respect filters and optional equivalent columns.

## Migration and installation

Use `FinanceTracker-v2.8.0-macOS.pkg` through Finder. The existing installer path, service, port, dependency installation, pre-upgrade backup and data/.venv preservation are unchanged. Production remains `/Applications/finance_tracker`, `com.adams.financetracker`, port 8080.

Startup applies the existing v2.7 additive migration if needed, then a v2.8 migration to extend SQLite's frequency CHECK constraint. The recurring-rules table is rebuilt atomically with all columns, IDs, calendar choices, values, indexes/triggers and AUTOINCREMENT state preserved. Recurring occurrence references and other financial tables are retained. Integrity/foreign-key checks reject a failed migration, and foreign-key enforcement is restored. Repeating migration is safe. No financial amounts or user/security settings are recalculated or reset.

Upgrades from v2.6.1, original v2.7.0 and the superseded fixes-only v2.7.0 schema are supported. To downgrade after using the new frequencies, restore the matching pre-upgrade database backup with the old application; do not open new-frequency schedules with an older scheduler.

## Validation limits

See `FinanceTracker-v2.8.0-TEST-REPORT.md` for exact results. Automated browser checks simulate desktop/iPad/iPhone widths. Physical Apple-device Print/Share, a live Installer/LaunchAgent restart and external Tailscale connectivity require validation on the deployment machine. Publishing this release does not install it over the live application.
