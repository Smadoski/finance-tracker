# Finance Tracker v2.9.0

Baseline: released v2.8.0 (`b405ffb85f3271c25d647d461674e35b731c69f5`).

## Financial Health

A new Financial Health report separates actual tracked balances, estimated operating finances, annualised retirement projections and interactive income scenarios. Net worth includes all active tracked accounts and asset classes, with liabilities deducted and unclassified assets explicitly reconciled.

Category, expense type, income type, spending classification, funding source and funding strategy are independent. Capital and exceptional purchases are excluded from normal living-cost estimates. Extraordinary receipts are excluded from recurring income and coverage, even when enabled in a scenario. Rent funded from capital remains normal expenditure.

Account classes are accessible, retirement, other, designated and needs review. Financial classifications can be reviewed in batches, searched by description/account, and applied separately to accounts, posted transactions, Pending and recurring rules. Recurring classifications flow into future automatic and Pending postings; changes never silently reclassify history.

Funding strategies provide an editable purpose, currency, monthly requirement, ordered accounts, optional designated allocations, start/end dates and change event. Housing has its own panel. Estimates show current/next sources, individual and combined runway and transition dates. Pension monitoring shows gross/net withdrawals, annual withdrawal percentage, cumulative recorded gross withdrawals and projected requirements. Known net shortfalls and shared funding accounts are flagged.

A linked strategy's end date caps forecasts **and future automatic recurring postings**, using the earlier of the rule and strategy end date. Extending an ended strategy does not automatically reactivate an ended recurring rule. Review and reactivate that rule explicitly when appropriate. Existing posted and Pending entries remain intact.

## Forecasts, scenarios and currency

The existing forecast is now labelled Scheduled Cash-Flow Forecast. Estimated Cash-Flow Forecast adds estimated unscheduled normal expenditure. Known scheduled capital purchases still affect scheduled cash flows, but are never extrapolated into ordinary spending. Extraordinary receipts are never extrapolated as recurring income.

Historical estimates use up to 12 complete months and divide by months with activity. Maturity is limited below three months, preliminary at three, established at six and mature at twelve. Empty months may mean missing records. Recurring equivalents plus positive historical residuals by account/category avoid double counting. Historical schedule equivalents, including ended schedules, are deducted conservatively; this can understate variable spending sharing the same category. Ended scheduled rent is not projected indefinitely. Historical income beyond scheduled amounts is explicitly an assumption about continuation.

Income scenarios run immediately in the browser using the loaded report. Individual sources and types can be toggled, with current position, no investment income, salary stops, pension only and salary plus pension presets. Scenario changes never write financial records. Aggregate capital runway excludes pensions and other assets; it does not automatically reallocate purpose-specific funds.

Currency exposure groups configured financial assets by account currency and shows current EUR equivalents and illustrative ±5% GBP sensitivity. It reuses the existing exchange-rate service. This release does not add exchange-rate providers or expand the existing account-currency choices; unsupported conversions fail explicitly rather than assuming parity.

Four-weekly, first-day and last-day scheduling, optional monthly/annual equivalents, and the frequency-grouped recurring report remain intact. Four-weekly normalization uses 13 annual payments.

## JSON export and iPad navigation

JSON generation no longer navigates the application window to a downloaded JSON response. The page prepares the file, then offers Save JSON and a separate Share JSON action where file sharing is supported. Native sharing starts directly from the share-button gesture. Completion, cancellation, errors and timeouts reset busy state; leaving the page aborts requests and releases object URLs. The save fallback opens separately, keeping application navigation available.

Exports retain existing top-level fields and add schema identifier `finance-tracker.financial-review/2.9`, Financial Health, classified posted/recurring entries and estimated forecasts. Account filtering also scopes financial-health calculations and suppresses funding strategies whose full account sequence is outside the selection. Credentials, raw settings, user records and receipt paths remain excluded.

Chrome and WebKit tests cover desktop, iPad and iPhone dimensions and export lifecycle/navigation. Native share success, cancellation and errors are simulated; no physical iPad/iPhone share-sheet or installed-PWA session was available for validation.

## Upgrade and first use

1. Keep a current backup and install the new package using the existing upgrade process. No database recreation is needed. The installer preserves data, receipts, secret key, security settings and the existing virtual environment.
2. Open Financial Health → Review classifications. Classify accounts, relevant historical transactions and recurring rules. Old records deliberately default to Needs review; amounts and category names are not used to guess classifications.
3. Configure funding purposes and account sequences. Use explicit allocations for shared accounts. Link normal recurring expenses to their strategies through Classifications.
4. For pension monitoring, enter known gross/net amounts and actual withdrawals. Monitoring entries do not post cash transactions or adjust pension valuations; continue recording those through the existing workflows.
5. To use the capital ledger, enter opening capital with the same opening date for all participating accounts. Classified extraordinary receipts and capital purchases since that date are included automatically. Enter other capital movements explicitly, including capital-funded living costs, without duplicating receipts/purchases already included.

Normal-cost and recurring-income estimates exclude unclassified entries and prominently report outstanding review counts. Retirement projections require at least three active complete months and reviewed asset/income/expense classifications. All sustainability, FX and runway figures are monitoring estimates; no returns, inflation, future tax or safe-withdrawal recommendation is assumed.

The migration is atomic, repeatable and additive. For rollback, retain a pre-upgrade database backup alongside its matching older application. Do not remove new tables/columns from a working database manually.

The macOS installer uses the existing offline wheelhouse and is unsigned. Its platform-specific wheels must match the target Python environment. Publishing this release does not install it over a live system.
