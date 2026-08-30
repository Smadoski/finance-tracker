# Finance Tracker v2.2.7 — Test Report

Validated:
- Python compilation passed.
- All Jinja templates parsed successfully.
- VERSION is 2.2.7 and postinstall verifies 2.2.7.
- category_rows calculates child_count directly from SQLite.
- category_options derives one explicit role: parent, subcategory, or category.
- Report selector uses the explicit role rather than inferring hierarchy independently.
- Subcategory labels contain parent/category path.
- Standalone top-level categories render as Category, not Parent.
- Report result rows show Parent total only for groups containing subcategories.
- Existing parent_id relationships are not migrated or rewritten.
- Required macOS scripts are executable and ZIP integrity is valid.
