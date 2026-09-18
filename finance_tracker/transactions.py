def expand_category_ids(conn, selected_ids):
    ids = set(int(x) for x in selected_ids)
    if not ids:
        return []
    q = ",".join("?" for _ in ids)
    children = conn.execute(f"SELECT id FROM categories WHERE parent_id IN ({q})", tuple(ids)).fetchall()
    ids.update(int(r["id"]) for r in children)
    return sorted(ids)


def delete_transaction_atomic(conn, transaction_id):
    """Retain occurrence history and remove only this transaction's linked transfer."""
    conn.execute('BEGIN IMMEDIATE')
    try:
        row=conn.execute('SELECT * FROM transactions WHERE id=?',(transaction_id,)).fetchone()
        if not row:
            conn.rollback()
            return None
        rows=conn.execute('SELECT id,receipt_path FROM transactions WHERE transfer_group=?',(row['transfer_group'],)).fetchall() if row['transfer_group'] else [row]
        ids=[r['id'] for r in rows]; marks=','.join('?' for _ in ids)
        # Keep status=posted so the deleted financial entry is never scheduled again.
        conn.execute(f"UPDATE recurring_occurrences SET transaction_id=NULL,detail='Posted transaction deleted by user; occurrence retained' WHERE transaction_id IN ({marks})",ids)
        conn.execute(f'DELETE FROM transactions WHERE id IN ({marks})',ids)
        conn.commit()
        return dict(transfer=bool(row['transfer_group']),receipts={r['receipt_path'] for r in rows if r['receipt_path']})
    except Exception:
        conn.rollback()
        raise
