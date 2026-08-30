# Finance Tracker v2.2.6 — Test Report

Validated:
- app.py compiles successfully.
- VERSION is 2.2.6.
- macOS postinstall expects VERSION 2.2.6.
- Category report expense values are converted to positive display values without changing database transaction signs.
- HTML and PDF category report paths use the same expense-sign treatment.
- Category Management supports assigning/removing parent relationships for existing categories.
- Parent relationship validation blocks self-parenting, parent-to-child nesting and mismatched category kinds.
- Required macOS installer/package scripts retain mode 0755 in the release ZIP.
- ZIP integrity verified.
