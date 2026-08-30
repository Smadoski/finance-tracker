# Finance Tracker v2.2.4

Corrective macOS installer release.

- Stops both legacy `com.finance.tracker` and current `com.adams.financetracker` LaunchAgents before upgrade.
- Stops any stale Finance Tracker listener on local port 8080 before replacing application code.
- Removes the legacy LaunchAgent plist after upgrade.
- Preserves the existing `data/` directory and backs up `finance.db` before upgrade.
- Verifies the installed VERSION is exactly 2.2.4 before restarting the service.
- Retains the v2.2.1 hierarchy and selective multi-account reporting changes.
