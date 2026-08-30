# Finance Tracker v2.0 update

This is a major release. Back up your existing database before updating.

## New in v2.0

- **Quick Entry** mobile-friendly screen for fast spending capture.
- A configurable **nominated Quick Entry account**.
- **Pending transactions**: quick entries do not alter balances until reviewed and posted.
- **Receipt capture from iPhone/iPad**, including the rear-camera shortcut where supported by Safari.
- **On-device OCR using Apple Vision** on the Mac mini. Receipt images stay local and are not sent to a cloud OCR service.
- Receipt parsing attempts to identify the merchant, date and total.
- Category suggestions learn from previous matching descriptions and use sensible merchant keywords as a fallback.
- Receipt images remain attached to the final transaction after posting.
- Backups now include a complete compressed snapshot of the `data` folder so receipt images are protected as well as the SQLite database.
- **Automatic GBP/EUR exchange rates** from the European Central Bank, checked once per day, with a manual refresh button and saved-rate fallback.
- Manual exchange-rate entry remains available.

## Updating an existing v1.x installation

1. Stop Finance Tracker.
2. From the existing installation folder run `./backup.sh`.
3. Keep the entire existing `data` folder safe. Do **not** replace it with an empty data folder.
4. Replace the program files with the v2.0 files while preserving your existing `data` folder.
5. Activate the virtual environment and reinstall requirements because v2.0 adds Apple Vision OCR support:

```bash
cd /Applications/finance_tracker
source .venv/bin/activate
pip install -r requirements.txt
```

6. Start Finance Tracker again.
7. Open **Settings**, choose the nominated Quick Entry account, and leave automatic exchange rates enabled if required.

The database is upgraded automatically on first start. v2.0 adds the pending-entry table and receipt/exchange-rate metadata without deleting existing accounts or transactions.

## iPhone Quick Entry

Open `http://YOUR-MAC-NAME.local:8080/quick` while at home, or use the Mac mini's Tailscale address when away from home. In Safari, use **Share > Add to Home Screen** for app-like access.

Do not expose port 8080 directly to the internet.
