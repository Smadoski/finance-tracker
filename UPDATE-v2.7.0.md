# Finance Tracker v2.7.0

## Financial planning

- Dashboard links to period income, spending, remaining targets, scheduled income and spending, and projected month-end cash.
- Targets retain the existing most-specific-target aggregation, with expandable parent groups, remaining amounts and scheduled period-end projections for weekly, monthly, quarterly and yearly periods.
- Upcoming shows the next 7 days, 30 days or this month. Forecast provides month-end and 30/60/90-day projections, account details and contributing scheduled transactions.
- Recurring rules offer weekdays-only, England/Wales or Cyprus bank calendars. See HOLIDAY-CALENDARS.md for scope and maintenance limitations.
- Advanced transaction search combines description, account, category/subcategory, date, signed native amount, type, user and posted/pending filters. Transaction CSV exports retain filters; targets also export to CSV.
- CSV import requires upload, preview/mapping, destination selection and explicit review. Suspected duplicates need separate approval. UTF-8 files support signed amounts or debit/credit columns, with a 2 MB / 5,000-row limit.
- Reports offers AI Financial Review JSON with calculated balances, category totals, targets, scheduled items, forecasts and optional 3/6/12-month history. Exporting does not send data to an AI service.
- Larger visible Adams-Home artwork and responsive planning cards.
- Posting/discarding recurring Pending entries now updates the occurrence audit before removing the pending row.

## Calculation methods

Forecasts use current posted cash balances plus unposted scheduled income minus scheduled spending and net transfers, using the existing GBP/EUR conversion. Cash includes current, savings, cash and Premium Bonds accounts. Windows include today; 30 days means today through day 29. No unscheduled spending or future exchange-rate changes are predicted. Past-due items outside the chosen window are excluded.

Target projections add remaining scheduled expenses to existing target actuals. Parent targets remain informational when more-specific child targets determine the overall total. Historical averages use months with recorded activity; objective first-to-last trends require three active months. Missing history is not interpreted as evidence of zero spending.

## Upgrade from v2.6.x

1. Take a backup before upgrading and stop the application service.
2. Install the v2.7.0 package, or replace application files while retaining the complete existing `data/` directory and its secret key.
3. Startup applies repeatable migrations automatically: a recurring calendar column defaulting to weekdays-only, search indexes and temporary CSV review storage. No financial amounts are rewritten and no manual SQL is needed.
4. Confirm the footer/Status version is 2.7.0, then check balances and recurring rules. Choose holiday calendars explicitly where wanted.

Restore both the previous application and the pre-upgrade database backup for a rollback. Package build validation does not constitute a production installation test. See the deep test report for precise validation and limitations.
