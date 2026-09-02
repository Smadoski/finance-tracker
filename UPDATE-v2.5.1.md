# Finance Tracker v2.5.1

This release refines selectable controls and responsive presentation without
changing financial calculations or the v2.5.0 database schema.

## Interface improvements

- Targets and recurring transactions use compact native HTML selectors for
  mutually exclusive choices.
- Target editing now provides a clear Category/Subcategory selector as well as
  Period and Currency selectors.
- Multi-account report selection remains a checkbox interface so several
  accounts can still be selected simultaneously.
- Target and recurring-rule tables become labelled card-style rows on narrow
  screens rather than forcing option and action controls beyond the viewport.
- Selectors use iOS-safe text sizing and touch heights; selector grids collapse
  cleanly at iPhone widths.
- Destructive actions remain visibly separated from routine actions.
- Status continues to hold application/system information. Settings continues
  to hold configurable values.

## Compatibility

There is no v2.5.1 schema migration. Existing transactions, recurring rules,
targets, licence values and configuration are retained during upgrade.
