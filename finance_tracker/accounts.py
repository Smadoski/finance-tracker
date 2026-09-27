def account_balance(conn, account):
    if account["account_type"] in ("pension", "other_asset", "liability"):
        row = conn.execute("SELECT value FROM valuations WHERE account_id=? ORDER BY valuation_date DESC,id DESC LIMIT 1", (account["id"],)).fetchone()
        return float(row["value"]) if row else float(account["opening_balance"])
    row = conn.execute("SELECT COALESCE(SUM(amount),0) s FROM transactions WHERE account_id=?", (account["id"],)).fetchone()
    return float(account["opening_balance"]) + (-1 if account['account_type']=='credit_card' else 1)*float(row["s"])


ACCOUNT_TYPES=('current','savings','premium_bonds','cash','pension','other_asset','liability','credit_card')
DEBT_TYPES=('liability','credit_card')


def validate_account_change(conn, account, new_type, currency, opening, confirmed=False):
    """Only explicit liability-to-card conversion may change an established ledger model."""
    import math
    if new_type not in ACCOUNT_TYPES or currency not in ('GBP','EUR') or not math.isfinite(opening):
        raise ValueError('Choose a valid account type, currency and finite opening balance.')
    if not account: return opening
    old=account['account_type']
    if old=='liability' and new_type=='credit_card':
        if not confirmed: raise ValueError('Confirm conversion to a credit card to preserve the current debt and retain valuation history.')
        if currency!=account['currency']: raise ValueError('Keep the existing currency when converting a liability.')
        if conn.execute('SELECT 1 FROM funding_steps WHERE account_id=?',(account['id'],)).fetchone():
            raise ValueError('Remove this liability from funding strategies before converting it.')
        # Preserve current debt even when historical transactions exist but were ignored by valuations.
        total=conn.execute('SELECT COALESCE(SUM(amount),0) FROM transactions WHERE account_id=?',(account['id'],)).fetchone()[0]
        return account_balance(conn,account)+float(total)
    history=any(conn.execute('SELECT 1 FROM '+table+' WHERE account_id=? LIMIT 1',(account['id'],)).fetchone()
                for table in ('transactions','valuations','pending_transactions','recurring_rules','funding_steps'))
    history=history or conn.execute('SELECT 1 FROM recurring_rules WHERE to_account_id=? LIMIT 1',(account['id'],)).fetchone()
    if currency!=account['currency'] and history:
        raise ValueError('An account with financial history cannot change currency. Create a separate account.')
    if history and new_type!=old and (old in ('pension','other_asset') or new_type in ('pension','other_asset')):
        raise ValueError('Create a separate account rather than changing how an existing ledger is valued.')
    if new_type!=old and (old in DEBT_TYPES or new_type in DEBT_TYPES):
        raise ValueError('Create a separate account for a different debt model, or explicitly convert a liability to a credit card.')
    return opening
