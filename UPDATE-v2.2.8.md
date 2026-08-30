# Finance Tracker v2.2.8

## Report category-selector hierarchy fix

This release targets the display defect observed with an existing relationship such as Motoring -> Petrol/Fuel:
the report calculation includes the subcategory correctly, but the selector previously displayed both entries as standalone categories.

Changes:
- Category hierarchy is normalized into explicit `is_parent` and `is_subcategory` boolean values on the server.
- The Reports selector uses those explicit values rather than independently inferring hierarchy.
- Category Management uses the same normalized values.
- Existing `parent_id` data is read only; this release does not rewrite category relationships.
- A top-level category with children displays as Parent.
- A category with a parent_id displays as Subcategory and shows its full parent/name path.
- A top-level category with no children displays simply as Category.
- All v2.2.7, v2.2.6 and installer/authentication fixes are retained.
