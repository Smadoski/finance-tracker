def account_balance(conn, account):
    if account["account_type"] in ("pension", "other_asset", "liability"):
        row = conn.execute("SELECT value FROM valuations WHERE account_id=? ORDER BY valuation_date DESC,id DESC LIMIT 1", (account["id"],)).fetchone()
        return float(row["value"]) if row else float(account["opening_balance"])
    row = conn.execute("SELECT COALESCE(SUM(amount),0) s FROM transactions WHERE account_id=?", (account["id"],)).fetchone()
    return float(account["opening_balance"]) + float(row["s"])
