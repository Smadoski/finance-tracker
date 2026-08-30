def save_category_parent(conn, category_id, parent_id):
    category_id = int(category_id)
    parent_id = int(parent_id) if parent_id not in (None, "") else None
    cat = conn.execute("SELECT * FROM categories WHERE id=?", (category_id,)).fetchone()
    if not cat:
        return False, "Category not found."
    if parent_id == category_id:
        return False, "A category cannot be its own parent."
    if parent_id is not None:
        parent = conn.execute("SELECT * FROM categories WHERE id=?", (parent_id,)).fetchone()
        if not parent:
            return False, "Choose a valid parent category."
        if parent["parent_id"] is not None:
            return False, "Subcategories cannot themselves be used as parents."
        if parent["kind"] != cat["kind"]:
            return False, "Parent and subcategory must be the same type."
        child_count = conn.execute("SELECT COUNT(*) n FROM categories WHERE parent_id=?", (category_id,)).fetchone()["n"]
        if child_count:
            return False, "This category already has subcategories. Move or remove them before making it a subcategory."
    conn.execute("UPDATE categories SET parent_id=? WHERE id=?", (parent_id, category_id))
    conn.commit()
    saved = conn.execute("SELECT parent_id FROM categories WHERE id=?", (category_id,)).fetchone()
    if not saved or saved["parent_id"] != parent_id:
        return False, "Category hierarchy could not be saved."
    return True, ("Category hierarchy updated." if parent_id is not None else "Category is now a top-level category.")

def selector_groups(conn):
    tops = conn.execute("""SELECT id,name,kind FROM categories
                           WHERE parent_id IS NULL
                           ORDER BY kind,name""").fetchall()
    groups = []
    for top in tops:
        children = conn.execute("""SELECT id,name,kind,parent_id FROM categories
                                   WHERE parent_id=?
                                   ORDER BY name""", (top["id"],)).fetchall()
        groups.append({
            "id": int(top["id"]),
            "name": top["name"],
            "kind": top["kind"],
            "is_parent": bool(children),
            "children": [dict(c) for c in children],
        })
    return groups
