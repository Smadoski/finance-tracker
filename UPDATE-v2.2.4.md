# Finance Tracker v2.2.4

## Authentication upgrade-persistence fix

- Finance Tracker no longer resets the optional-login preference during an upgrade.
- The `auth_required` setting remains in the existing `data/finance.db`, which the macOS installer preserves.
- If password protection was disabled before installation, both Finance Tracker and Quick Entry remain password-free after the upgrade.
- Clean installations now default application authentication to disabled; it can be enabled from Settings.
- Existing users and password hashes are retained, so authentication can be re-enabled later.
- Includes all v2.2.3 fixes and v2.2.1 reporting/category hierarchy enhancements.
