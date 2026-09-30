# Finance Tracker roadmap

Reconciled against the v2.10.0 prepared build on 2026-09-27. The published baseline
remains v2.9.0 until release promotion. VERSION is 2.10.0 for the prepared installer.

## Implemented for v2.10.0

- Balances-first Home using the existing two selected-account settings as favourites;
  separate available cash and debt, optional combined position, five recent entries,
  Pending/uncategorised/upcoming attention links. Existing summaries live in Reports.
- Credit-card transaction type, purchases, explicit expense refunds and linked
  repayment transfers; debt-aware net worth and separate card forecasts.
- Explicit liability-to-card conversion preserving current debt and historical
  valuations. Existing liabilities are never converted automatically.
- Consistent expense refunds across targets, reports, Financial Health and exports.
- Repository-based working instructions and release/status records.

See UPDATE-v2.10.0.md and FinanceTracker-v2.10.0-TEST-REPORT.md for semantics,
acceptance evidence and deployment limits. No interest/minimum-payment automation
or automatic card settlement is included; schedule known repayments explicitly.

## Remaining release actions

Review the prepared change and installer, then authorise promotion/publication and,
separately, live deployment. Physical-device Print/Share and live service restart
validation remain outstanding. Do not reopen implemented work as a new feature
without a reproducible regression or a further requirement.

## Already delivered — retain and regression-check

| Request | Repository evidence | Remaining work |
| --- | --- | --- |
| Recurring Transactions Report | v2.8 notes; finance_tracker/recurring_report.py, recurring_report_routes.py; templates/recurring_report.html | Implemented: frequency groups, filters, original amounts, optional monthly/annual equivalents, PDF/CSV. Preserve; do not rebuild. |
| Additional recurrence options | finance_tracker/frequencies.py and recurring.py; tests/test_v280_release.py | Implemented: four-weekly, first/last day, fortnightly, six-monthly. Four-weekly uses 13 payments per 52 weeks; EUR 100 → EUR 108.33/month equivalent. Preserve leap-year and holiday behavior. |
| Transaction-delete 500 | v2.8 notes; tests/test_v280_release.py deletion/rollback/transfer tests | Known recurring-occurrence foreign-key failure fixed. If still reported on v2.9, collect a fresh reproduction and traceback before claiming the same cause. |
| PDF Print/Share | templates/pdf_actions.html; v2.8 notes/test report | Explicit View, Save, Print and Share actions implemented. Physical Apple-device print/share remains unverified; verify the affected device/browser and output before closing the user-visible issue. |
| Liability display/net worth | app.py dashboard/net-worth and finance_tracker/accounts.py | Existing valuation-based support; transaction-based cards are implemented in the prepared v2.10.0 build above. |

## Release gate

Keep the v2.9 Financial Health, funding, classification and export functionality.
Record actual implementation, automated results and device checks separately.
Follow RELEASE-WORKFLOW.md; publication and live deployment are separate steps.
