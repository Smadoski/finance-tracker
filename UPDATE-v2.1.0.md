# Finance Tracker v2.1.0
- Adds parent categories and subcategories with automatic in-place SQLite migration.
- Existing transactions can be re-categorised individually from Transactions or in bulk from Categories.
- Category reports now total parent categories and show subcategory breakdowns, with PDF export.
- Adds Adams-Home branding.
- Changes the web service to loopback-only and adds Tailscale Serve scripts for private Tailnet access, matching Document Archive.
- Adds macOS background service management scripts.

## Upgrade
1. Stop Finance Tracker and run `./backup.sh` in the existing installation.
2. Replace the application files with this release, but **keep your existing `data` folder**.
3. Run `./start.sh` once. The database migration adds `parent_id` to Categories without deleting transactions.
4. For background operation from `/Applications/finance_tracker`, run `./install-service.sh`.
5. Run `./tailscale-serve.sh` to publish Finance Tracker privately to your Tailnet on HTTPS port 8443. This avoids replacing Document Archive's Tailscale Serve mapping on HTTPS port 443.
