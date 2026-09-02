# Finance Tracker v2.5.0

## New functionality

- Recurring expenses, income and linked transfers with daily, weekly, monthly,
  quarterly and annual schedules.
- Exact-date, previous-working-day and next-working-day posting. A working day
  in this release is Monday to Friday; public-holiday calendars are deliberately
  deferred.
- Automatic or Pending-for-review posting, pause/resume, skip-next, post-now,
  overdue catch-up and a persistent occurrence audit trail.
- Weekly, monthly, quarterly and yearly category/subcategory targets with Target,
  Actual, Variance, % Used and status reporting.
- The System page is now labelled Status. Read-only version, authorship and
  licence information has moved from Settings to Status; licence configuration
  remains in Settings and existing values are preserved.

## Database migration

The repeatable v2.5.0 migration adds `recurring_rules`,
`recurring_occurrences`, and `category_targets`. The unique key on
`(rule_id, scheduled_date)` prevents a due occurrence being generated twice
after restarts or repeated scheduler runs. Existing transaction, licence and
configuration rows are not rewritten.

## Budget aggregation rule

Targets use a most-specific-target-wins rule for overall totals. When a parent
category and one or more of its subcategories both have targets for the same
period, the parent row remains visible for comparison but is excluded from the
overall target and actual totals. This prevents the same target scope and child
transactions being counted twice.

## Upgrade notes

- Upgrade directly over v2.4.7 with the v2.5.0 macOS package.
- The existing data directory, licence values, security configuration and
  service configuration are retained.
- The planned integer-money storage migration is not included in this release.

