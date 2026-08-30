# Finance Tracker v2.2.7

## Category hierarchy cleanup

This release replaces the ambiguous two-state category presentation with a single consistent three-role hierarchy:

- Parent — a top-level category that actually has one or more subcategories.
- Subcategory — a category whose parent_id points to a parent category.
- Category — a standalone top-level category with no subcategories.

Changes:
- Category Management and Reports use the same server-side category classification.
- Report category selection shows subcategories indented with their full path, e.g. Entertainment / Eating Out.
- Standalone categories are no longer incorrectly labelled Parent.
- Parent totals in report output are labelled Parent total only when the report group genuinely contains subcategories.
- Existing stored parent_id relationships are retained; no category data is rewritten.
- Retains positive expense presentation introduced in v2.2.6.
- Retains macOS installer permission and authentication-persistence fixes from v2.2.5/v2.2.4.
