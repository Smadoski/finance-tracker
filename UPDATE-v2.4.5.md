# Finance Tracker v2.4.5

Installer, recovery and Dropbox reliability release.

- Administrator recovery mode is restricted to genuine local access; reverse-proxied Tailnet/LAN clients are rejected even when the proxy connects over loopback.
- Dropbox retries use bounded backoff rather than retrying on every request.
- A pending Dropbox backup is protected from normal local-retention deletion.
- Dropbox retry count/next retry state is persisted.
- Preinstall stops only stale processes whose command line identifies /Applications/finance_tracker.
- Installer fails clearly if Python 3 is missing.
- Mac package build now downloads and bundles a dependency wheelhouse.
- Postinstall installs Python dependencies only from the bundled wheelhouse (`--no-index --find-links`), so the resulting .pkg does not need internet access for Python packages.
- LaunchAgent bootstrap/kickstart failures are no longer ignored.
- Postinstall performs a local HTTP health check before Apple Installer reports success.
- Retains all v2.4.4 and earlier transaction-integrity, Read Only, credentials, receipt, backup, Dropbox Keychain and report-sharing fixes.

Runtime note:
The generated .pkg is offline with respect to Python package dependencies, but still requires a working Python 3 runtime on the target Mac. The installer now fails clearly if Python 3 is unavailable.

- Installer and package builder explicitly discover Homebrew Python at `/opt/homebrew/bin/python3` and `/usr/local/bin/python3` as well as normal PATH locations.
