# Finance Tracker v2.4.6

Corrective release built directly from the user-supplied v2.4.5 bugfixed source.

Included:
- Dashboard Other Assets reconciliation bucket, hidden when zero.
- Friendly account-add validation for invalid opening balance/currency.
- delete_pending receipt cleanup through delete_if_unreferenced.
- SQL LIKE wildcard escaping in category suggestion matching.
- account_pdf date validation and reversed-date normalisation.
- All v2.4.5 installer, backup, Dropbox, Tailnet, credentials, transaction, transfer and receipt protections retained.

Known outstanding:
- Native iPhone/iOS report sharing is not fixed in this release and remains scheduled corrective work.

Architecture:
- Complete the staged Blueprint/module extraction before the integer-money migration.
