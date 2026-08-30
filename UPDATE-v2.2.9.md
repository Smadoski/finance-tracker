# Finance Tracker v2.2.9

## Category selector hierarchy rebuild

The Reports category selector no longer uses a flat category list or template-side hierarchy inference.

Instead:
- the server queries top-level categories directly;
- for each top-level category it queries its actual child categories using parent_id;
- each parent is rendered immediately followed by its real subcategories;
- a top-level category with children is labelled Parent;
- a child is labelled Subcategory and displays as Parent / Child;
- a top-level category with no children is labelled Category;
- existing category data is not changed.

This directly addresses the case where Motoring correctly includes Petrol/Fuel in report calculations but the selector still displayed both as standalone categories.

Also retained:
- credentials default OFF for clean installs;
- existing authentication preference preserved on upgrades;
- positive expense totals;
- multi-account reporting;
- macOS installer permission fixes.
