# Finance Tracker v2.10.0 validation

Validation date: 27 September 2026. Baseline: published v2.9.0,
`8da294e13fbdc8dabd9741de5469a90a09dfbd26`. Release status: prepared build,
not a published release or tested live installation.

## Automated checks

Full suite: `python -m pytest -q --tb=short` with the existing project virtual
environment: **254 passed, 0 failed, 0 skipped**, 11.80 seconds. Includes all 233
baseline tests plus 21 v2.10 acceptance cases. Existing navigation assertions now
expect Home and the Reports overview; the current-version assertion expects 2.10.0.
Historical export fixtures retain their explicit versions.

New coverage includes purchases, refunds, edits, deletion of both repayment legs,
credit balances, GBP/EUR repayments, debt/net-worth reconciliation, explicit
conversion with historical valuations/transactions, Quick Entry/Pending, CSV refunds,
forecast/posting reconciliation, export allowlists, classified normal-cost refunds,
capital refunds, favourites, archived accounts and read-only access protection.
Compilation and diff whitespace checks also pass.

## Browser and visual checks

Chrome and WebKit; desktop 1440×1000, iPad 820×1180 and iPhone 390×844.

- **78 new page/engine/viewport checks** passed with no document overflow or
  JavaScript errors. Expanded entry forms, card selection, current navigation,
  separate debt forecasts and combined-position disclosure were checked.
- Both favourite balances fit in the initial viewport at every tested size.
- **150 retained page/engine/viewport checks** and **42 Financial Health / JSON
  export lifecycle checks** passed with no failures or JavaScript errors.
- JSON save, simulated native-share success/cancel/error, HTTP failure and timeout
  leave navigation usable. Original schema identifier remains 2.9; metadata is 2.10.0.
- Desktop and iPhone screenshots were inspected; recent transactions use compact
  rows on mobile rather than the larger transaction-management card layout.

Reproduce using tests/serve_browser_fixture.py (disposable synthetic copy),
tests/browser_v2100.cjs and tests/browser_v290.cjs as described in DEVELOPMENT.md.
No real financial data is included in browser fixtures or screenshots.

## Upgrade and installer rehearsal

Created a synthetic database using source from tag v2.9.0, including a bank,
valuation liability, historical transaction, four-weekly rule, favourites and
security settings. After replacing code and repeating v2.10 startup twice, every
row in every application table matched the original snapshot. Balances, the
secret key and settings were retained. SQLite integrity and foreign-key checks
passed. No schema extension or automatic account conversion is required.

Built and expanded the existing macOS installer. Rehearsed its packaged preinstall
and postinstall scripts against a separate temporary v2.9 installation. Verified
byte-identical pre-upgrade database backup; preservation of data, synthetic receipt,
secret, security settings and an existing virtual-environment marker; offline wheel
installation; v2.10 import and database integrity. Service/process control and
console-user discovery were stubbed, and all paths redirected to the temporary
installation. This does not claim a native Installer/LaunchAgent restart test.

## Packaging and release gate

Build using build-macos-pkg.sh and build-release-zip.sh from the committed release
branch. Expand the final installer and compare application files with that commit;
verify VERSION/PackageInfo, exclude data/secrets/caches/old assets, and generate
SHA-256 checksums alongside the delivered installer and ZIP. The final task result
records completion of these asset checks. Do not equate a local package with a
GitHub Release or a live deployment.

## Limits

No live installation, production-data modification, physical iPad/iPhone share
sheet, physical printing or external Tailscale test was performed. Native share
responses are simulated. The unchanged PDF actions still require verification on
the user's affected physical device. The installer is unsigned and retains the
existing platform-specific offline wheelhouse (build host Python 3.14/macOS).
Known repayments must be recorded or scheduled explicitly; interest, minimum
payments and automatic card settlement are not calculated.
