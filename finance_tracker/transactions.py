def expand_category_ids(conn, selected_ids):
    ids = set(int(x) for x in selected_ids)
    if not ids:
        return []
    q = ",".join("?" for _ in ids)
    children = conn.execute(f"SELECT id FROM categories WHERE parent_id IN ({q})", tuple(ids)).fetchall()
    ids.update(int(r["id"]) for r in children)
    return sorted(ids)
