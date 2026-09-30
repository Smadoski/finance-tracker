# Finance Tracker v2.10.0

Build baseline: published v2.9.0, commit
`8da294e13fbdc8dabd9741de5469a90a09dfbd26`. This is a prepared release build;
publication and live installation are separate actions.

## Home and Reports

Home puts your two favourite account balances first. Existing Dashboard account
1/2 selections carry forward unchanged; choose favourites in Settings. Archived
accounts disappear from this section. Available cash includes current, savings
and cash accounts, excluding Premium Bonds and investments. Cards/liabilities
appear separately. Expand Combined position for cash less debt and full net worth.
GBP and EUR totals are two equivalents of the same position, not additive amounts.

Recent transactions are limited to five compact rows, with View all. Attention
links show Pending, uncategorised transactions and upcoming scheduled items.
The previous aggregate balances and planning summary remain in Reports & Insights,
with links to category and recurring reports, Financial Health and AI review.
Existing navigation and planning features remain available.

## Credit cards

Add an account of type **Credit card**, entering the amount owed as a positive
opening balance. A negative balance represents a credit in your favour.

- A purchase is an expense with a negative transaction amount and increases debt.
- Tick **Refund of an expense** and select its original expense category to reduce
  debt and offset spending. This works in Transactions and Quick Entry/Pending.
- Repay via **Transfer**, from the bank account to the card. Both linked entries
  are retained, and the repayment is excluded from expenditure totals. Deleting
  a transfer removes both sides together. Different GBP/EUR amounts are supported.
- Manual entry, CSV, recurring postings, Pending, account statements and reports
  accept credit-card accounts. CSV uses negative spending and positive refunds;
  record repayments once through Transfer, rather than importing both sides as
  unrelated expenses/income.
- Scheduled and estimated forecasts show card debt separately from cash. Only
  recorded/scheduled repayments reduce projected cash; the application does not
  invent minimum payments, interest or automatic full-balance settlement.
- Card debt is deducted from net worth; a card credit increases it. Cards cannot
  be used as asset funding sources. Classified card spending contributes to normal
  costs; expense refunds offset spending rather than becoming income.

Existing **Liability (valuations)** accounts retain their original behaviour.
To convert one, edit it, choose Credit card and tick the explicit conversion box.
The current valued debt is preserved, including any historical transactions that
were previously ignored by the valuation model. The opening balance is calculated
as current debt plus the signed historical transaction total. Retained valuations
remain visible as history; future balances use the transaction ledger. Conversion
and its balance calculation are atomic. A conversion back to valuations is blocked
to avoid silently hiding transactions. Create a separate account for a different
model. Accounts with financial history cannot change currency.

Refund interpretation now consistently offsets expense totals in category reports,
targets, search/AI review, Financial Health and capital monitoring. Stored historical
amounts are not rewritten. Existing positive entries under expense categories are
therefore treated as refunds, rather than counted as additional expenditure.

## Upgrade and rollback

Use the usual Finder-compatible macOS installer with a current backup. No schema
change or automatic account conversion is needed: the database schema marker stays
2.9.0 while the application/package version becomes 2.10.0. Existing data, favourites,
security settings, receipts and valuations are retained. Review any existing cards
recorded as valuation liabilities and convert them explicitly when ready.

After creating or converting credit-card accounts, do not open the modified data
with v2.9.0: it does not understand the new debt model. Roll back with the matching
pre-upgrade database backup and application together.

The JSON schema identifier remains `finance-tracker.financial-review/2.9`; application
metadata reports 2.10.0 and forecasts add a separate `cards` array. Its fields follow
the same export allowlist as existing cash projections.

See [validation and limits](FinanceTracker-v2.10.0-TEST-REPORT.md). The package is
unsigned and includes wheels for the build host's Python/macOS environment, as in
previous releases. Physical-device Print/Share and a live service restart are not
claimed as tested by this build.
