# Finance Tracker v2.6.1 verification

Date: 4 September 2026

## Automated tests

Full regression suite: **77 passed, 0 failed, 0 skipped** (Python 3.11).
The v2.6.0 version-display assertion was updated to the new release version;
existing behavioural tests were retained. New tests cover all 14 destinations,
active state, open-by-default desktop markup, matching breakpoints, native menu
control, close/escape logic and preservation of role-restricted navigation.

## Browser checks

Using an isolated loopback application copy, all 14 destinations (the requested
13 plus Valuations) were clicked and returned to Dashboard at widths 1440, 1280,
1024, 768, 844 and 390px: **84 route/viewport checks passed**.

- Desktop links visible without opening a menu.
- Mobile Menu visible, opens all destinations and closes after navigation.
- Active page correctly highlighted on every destination.
- No navigation link overlap or horizontal navigation overflow.
- Header/menu did not cover the main content.
- Boundary checks at 900 and 901px passed, including resizing and Escape closure.
- Desktop (1440px) and expanded mobile (390px) screenshots visually inspected.

These were browser viewport simulations. No physical iPhone/iPad or Safari-device
testing was performed. The shared native disclosure also has an open HTML fallback.

## Upgrade fixture and data safety

The released v2.6.0 commit was extracted to a temporary directory, initialised,
and seeded with synthetic account/transaction/licence/configuration values.
After overlaying the v2.6.1 runtime changes, startup and Dashboard HTTP 200 passed.
Schema and all 12 application tables matched the baseline. SQLite's internal
category AUTOINCREMENT counter advances during the existing `INSERT OR IGNORE`
startup seeding; no category rows or user configuration changed. No financial
storage migration is part of this release.

Live financial data and `/Applications/finance_tracker` were not modified.
Actual Apple Installer/LaunchAgent upgrade and real Tailnet/Dropbox connectivity
were not exercised. Those operational checks remain for deployment acceptance.

## Packaging

ZIP and macOS PKG use the unchanged established build scripts. Release checks
include ZIP integrity, expanded PKG version and navigation payload, Python/shell
syntax, and exclusion of caches, test databases, data directories, environment
files, Git metadata, credentials and tokens. Offline wheels are retained.
The macOS PKG is unsigned; it is not signed or notarised by this release.
