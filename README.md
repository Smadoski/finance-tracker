# Household Finance Tracker v1.0

A private, self-hosted finance tracker designed for a Mac mini and shared household use.

## Included in v1.0

- GBP and EUR accounts
- Current, savings, cash and Premium Bond accounts
- Pension pots and other assets using dated valuations
- Liabilities and true net-worth calculation
- Manual transactions with categories, free-form tags and notes
- Transfers, including GBP/EUR transfers where the amount sent and received differ
- Household reporting currency (GBP or EUR)
- Manual GBP/EUR exchange-rate history
- Multi-user logins with administrator/member roles
- PDF account statements and PDF net-worth statements
- SQLite database stored locally on the Mac mini
- Backup script
- Responsive browser interface for Mac, iPad and iPhone

Open Banking is intentionally not included in v1.0. It can be added later through an authorised Open Banking provider without redesigning the financial data model.

# Mac mini installation

These instructions assume macOS and an administrator account on the Mac mini.

## 1. Install Python

Open Terminal and check:

```bash
python3 --version
```

If Python 3.11 or later is available, continue. If not, install the current Python 3 release from python.org, then reopen Terminal.

## 2. Copy the application

Copy the `finance_tracker` folder to a permanent location, for example:

```text
/Users/YOURNAME/Applications/finance_tracker
```

Do not run it permanently from Downloads.

## 3. Create the private Python environment

In Terminal:

```bash
cd ~/Applications/finance_tracker
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 4. First test

Run:

```bash
./start.sh
```

On the Mac mini open Safari and visit:

```text
http://localhost:8080
```

The first screen asks you to create the administrator account. Use a strong, unique password of at least 10 characters.

To stop the test server, return to Terminal and press Control-C.

## 5. Access from another device at home

On the Mac mini open System Settings > General > Sharing and note the Mac's local hostname. You can normally try:

```text
http://YOUR-MAC-NAME.local:8080
```

Alternatively find the Mac mini's LAN IP address in System Settings > Network and use, for example:

```text
http://192.168.1.50:8080
```

Do not configure port forwarding on the internet router.

## 6. Add the second household user

Sign in as administrator, open **Users**, and create the second user. `Member` is sufficient for normal transaction and valuation entry; `Administrator` also permits settings and user management.

## 7. Configure the finance system

Recommended order:

1. Settings: choose GBP or EUR as the reporting currency and enter the current GBP/EUR rate.
2. Accounts: add current accounts, savings accounts and Premium Bonds.
3. Accounts: add pension pots as type `Pension pot`.
4. Accounts: add any other assets or liabilities.
5. Valuations: record the latest pension/asset values.
6. Categories: add any personal categories you need.
7. Transactions: begin entering income and expenditure.
8. Transfer: use this screen when moving money between your own accounts, especially GBP/EUR transfers.

For Premium Bonds, enter the holding as the opening balance. A prize paid to a current account should normally be entered in the receiving current account with category `Premium Bond Prize`; this leaves the Premium Bond capital unchanged.

## 8. Automatic start after reboot

First determine the full application path:

```bash
cd ~/Applications/finance_tracker
pwd
```

Copy `com.finance.tracker.plist.example` to:

```text
~/Library/LaunchAgents/com.finance.tracker.plist
```

Edit it in TextEdit and replace:

```text
REPLACE_WITH_FULL_PATH
```

with the full path printed by `pwd`.

Then load it:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.finance.tracker.plist
```

After the next login/reboot, the finance server should start automatically.

To check its log:

```bash
tail -50 /tmp/finance-tracker.log
```

and errors:

```bash
tail -50 /tmp/finance-tracker-error.log
```

## 9. Backups

The important file is:

```text
data/finance.db
```

Run a manual backup with:

```bash
./backup.sh
```

It creates a standalone database backup and, in v2.0, a complete data snapshot containing the database and receipt images in:

```text
~/Documents/FinanceTrackerBackups
```

The script retains 90 days of backup files. For stronger protection, make sure the backup folder itself is covered by Time Machine or another backup system. A backup kept only on the same Mac does not protect against loss or disk failure.

## 10. Secure access away from home

Recommended: install Tailscale on the Mac mini and on the iPhone/iPad/Mac that will access it remotely. Sign all devices into the same Tailscale network. Then use the Mac mini's Tailscale hostname/IP followed by `:8080`.

Do **not** expose port 8080 directly to the public internet.

For an eventual production setup, HTTPS can also be added through a reverse proxy, but for a private Tailscale-only installation the encrypted Tailscale tunnel provides the transport security.

# Updating the application

Before replacing program files:

```bash
./backup.sh
```

Do not delete the `data` folder. It contains the database and application secret key.

# Restoring after a failure

1. Install a fresh copy of the application.
2. Create `.venv` and install `requirements.txt`.
3. Stop the Finance Tracker service.
4. Replace `data/finance.db` with the selected backup database.
5. Preserve the original `data/.secret_key` when possible; otherwise existing browser sessions will simply be invalidated.
6. Restart the service.

# Important security notes

- Use strong, unique passwords.
- Do not forward port 8080 from the router to the Mac mini.
- Keep macOS and Python security updates current.
- Use Tailscale or another private VPN for remote access.
- Keep independent backups.
- This application is for personal financial tracking; it is not accounting, tax, investment, or regulatory advice.

## Version 1.1 additions

Version 1.1 adds dual GBP/EUR dashboard values, category reporting by date range with PDF export, and account editing/archiving. Existing v1.0 databases are compatible; no migration is required. See `UPDATE-v1.1.md` before updating an existing installation.

## Version 2.0 additions

Version 2.0 adds mobile Quick Entry, pending review/posting, local Apple Vision receipt OCR with retained receipt images, category suggestions and automatic daily ECB GBP/EUR reference rates. Existing v1.x databases are migrated in place on first start. See `UPDATE-v2.0.md` before updating an existing installation.


# v2.1.0 additions

Finance Tracker v2.1.0 adds hierarchical categories/subcategories, individual and bulk re-categorisation of existing transactions, parent/subcategory reporting, Adams-Home branding, and private Tailscale Serve access.

The application now listens on `127.0.0.1:8080` only. Run `tailscale-serve.sh` (macOS) or `tailscale-serve.ps1` (Windows) after Tailscale is installed and signed in. Finance Tracker uses Tailnet HTTPS port **8443** so it can coexist with Document Archive on the same host without replacing Document Archive's port-443 Serve configuration.

When upgrading, preserve the existing `data` directory. On first launch the SQLite schema is migrated in place to add category hierarchy support; existing transactions and balances remain in the database.


## v2.4.2 hardening
Built from v2.4.0 and supersedes the undeployed v2.4.1. Dropbox tokens use macOS Keychain. Money remains REAL/float until v2.5.0.
