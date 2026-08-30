# Finance Tracker v2.2.6

## Category reporting and hierarchy fixes

- Expense totals in Category & Subcategory reports are now shown as positive "amount spent" values.
- The underlying transaction values remain unchanged, so account balances are unaffected.
- The PDF category report uses the same positive expense presentation.
- Existing categories can now be assigned to a parent category from Category Management.
- An existing subcategory can be returned to top-level status.
- Parent assignment is protected against self-parenting, nested subcategories and mismatched category types.
- Parent and Subcategory badges now reflect the stored hierarchy rather than leaving older flat categories permanently stuck as Parent.
- Retains v2.2.5 macOS installer permission fixes and all earlier v2.2.x changes.
