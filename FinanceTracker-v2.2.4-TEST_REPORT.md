# Finance Tracker v2.2.4 — Build Test Report

- Built from Finance Tracker v2.2.3.
- VERSION set to 2.2.4.
- Python source compilation checked.
- Jinja templates parsed where Jinja is available.
- Authentication preference remains stored in the preserved SQLite data directory.
- Installer preinstall excludes `data` from application-code removal.
- macOS package payload excludes `data`, so package installation cannot overwrite the existing database.
- Clean database default for `auth_required` is now `0` (disabled).
- Existing databases retain their stored `auth_required` value via INSERT OR IGNORE migration logic.
- macOS `.pkg` must be generated on macOS using the included Build Finance Tracker Installer.command / build-macos-pkg.sh because Apple pkgbuild/productbuild are not available in this build environment.
