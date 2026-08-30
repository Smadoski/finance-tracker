# Finance Tracker v2.4.4

- Requires at least one active Administrator before credentials can be enabled.
- Eliminates login/setup lockout and supports Administrator recovery.
- Installer no longer ignores dependency-installation failures.
- Preinstall no longer kills unrelated processes using port 8080.
- Failed Dropbox uploads are retried independently of local backup cadence.
- Settings shows last successful Dropbox backup separately.
- Adds stronger transaction, transfer and valuation validation.
- Rejects zero-value transfers.
- Retains all v2.4.3 security, transaction-integrity, receipt, backup, Dropbox and sharing fixes.

A truly network-independent macOS .pkg still requires the Mac build host to populate a compatible wheelhouse before packaging.
