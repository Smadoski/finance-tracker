# Finance Tracker v2.3.0

## Category hierarchy persistence + no-login release

Category hierarchy
- Parent assignments are now verified immediately after saving.
- Category Management shows an explicit Current Parent column.
- Existing category data is preserved.
- If a hierarchy update does not persist, Finance Tracker reports an error rather than claiming success.

Authentication
- Application-level credentials are intentionally disabled in this release.
- New installations default auth_required to 0.
- Upgrades explicitly set auth_required to 0 in the existing database.
- The installer verifies auth_required=0 before completing.
- Main Finance Tracker and Quick Entry should open without a Finance Tracker username/password prompt.
- Tailnet/Tailscale remains the intended access boundary.

All v2.2.9 hierarchy-rendering, positive expense totals, multi-account reporting and installer permission fixes are retained.
