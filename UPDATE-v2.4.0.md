# Finance Tracker v2.4.0

Architecture & Maintainability Release.

- Introduces finance_tracker package modules for database, accounts, transactions, categories, money, reports, receipts, security and settings.
- Keeps Flask route registration in app.py for compatibility while reusable logic moves into modules.
- Adds route-boundary modules for staged future Blueprint extraction.
- Expands automated regression tests with service-level and Flask test-client cases.
- Preserves the v2.3.2 database schema and user-facing behaviour.
- Does not perform the planned REAL/float money migration; that remains scheduled for v2.5.0.
