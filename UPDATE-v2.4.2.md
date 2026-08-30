# Finance Tracker v2.4.2
Built directly from v2.4.0; v2.4.1 was not used as the release base.

Fixes: explicit Quick Entry expense/income type; linked transfer deletion; receipt cleanup; posted transaction editing; expanded user management; login throttling; cookie hardening; content-validating receipt upload; SQLite backup API; automatic Dropbox uploads; macOS Keychain Dropbox token; report sharing; backup/dropbox/licence settings; repaired pytest fixture. Money remains REAL/float pending the controlled v2.5.0 migration.
- Existing Pending entries infer their new Expense/Income type from their stored amount sign during migration.
- Linked transfer legs cannot be independently recategorised.
