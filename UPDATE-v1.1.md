# Finance Tracker v1.1 update

This update adds:

- Dashboard values shown in both GBP and EUR.
- Category reporting by date range, with account and category-type filters.
- Drill-down from category totals to the individual transactions.
- PDF export of the category report.
- Edit Account screen, including account type, currency, opening balance, institution, notes, and archive status.

## Important: preserve your existing data

Your live database is stored at:

`/Applications/finance_tracker/data/finance.db`

Do not delete or replace the `data` folder when installing this update.

## Recommended update procedure

1. Back up the existing database:

```bash
cd /Applications/finance_tracker
cp data/finance.db ~/Desktop/finance-backup-before-v1.1.db
```

2. Stop Finance Tracker if it is running in a Terminal window with `Ctrl+C`. If you installed it as a launchd service, unload/restart it using the same method used in the original installation guide.

3. Copy these v1.1 items over the matching items in `/Applications/finance_tracker`:

- `app.py`
- `templates/`
- `static/`
- `VERSION`

Do not replace the existing `data/` folder.

4. Restart Finance Tracker.

5. Refresh the browser. You should see a new `Reports` navigation item and dual GBP/EUR figures on the Dashboard.

No database migration is required for v1.1.
