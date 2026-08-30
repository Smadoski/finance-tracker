# Updating Finance Tracker to v1.2

Version 1.2 fixes transaction sign handling across all normal transaction accounts.

## What changed

- Transactions assigned to an **Expense** category are now always stored as negative values.
- Transactions assigned to an **Income** category are now always stored as positive values.
- You can therefore enter `27.50` for either an income or expense and let the selected category determine the direction.
- Transfers continue to be handled by the dedicated Transfer screen and are unchanged.
- Uncategorized transactions retain the sign you type because there is no category type from which to infer the direction.
- Existing database structure is unchanged; no migration is required.

## Important: existing transactions

This update does **not** automatically alter transactions already stored in your database. That is intentional, because automatically flipping historical values could change legitimate data. Correct any known mis-signed transactions before or after the update.

## Safe update procedure on the Mac mini

Your live data is in `data/finance.db`. Do not replace or delete the `data` folder.

1. Back up the database:

```bash
cd /Applications/finance_tracker
./backup.sh
```

2. Stop Finance Tracker:

```bash
launchctl unload ~/Library/LaunchAgents/com.finance.tracker.plist
```

3. Replace the application program files with the v1.2 files, **preserving the existing `data` folder**.

4. Activate the existing virtual environment and ensure dependencies are installed:

```bash
cd /Applications/finance_tracker
source .venv/bin/activate
pip install -r requirements.txt
```

5. Start Finance Tracker:

```bash
launchctl load ~/Library/LaunchAgents/com.finance.tracker.plist
```

6. Refresh the browser and confirm the footer/version display shows v1.2 if shown by your installation.

## Quick test

Create a small test expense, for example `1.23`, using an Expense category. The account balance should decrease by 1.23. Then delete the test transaction.
