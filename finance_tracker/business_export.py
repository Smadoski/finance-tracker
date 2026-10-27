"""Read-only, local Business transactions contract. No web-app import or startup writes.

Stable transaction identifiers are the integer primary keys of the transactions
table; they are what integrations store as links. Amounts are exact-decimal
strings. Transfer legs share a transfer_group so GBP→EUR conversion pairs can be
recognised without ambiguity.
"""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
import json
import sqlite3
import sys

CONTRACT = 'business-transactions-v1'


def _day(value):
    if value and len(value) == 10 and value[4] == '-' and value[7] == '-':
        try:
            year, month, day = int(value[:4]), int(value[5:7]), int(value[8:10])
            datetime(year, month, day)
            return value
        except ValueError:
            pass
    raise ValueError('Dates must use YYYY-MM-DD.')


def _amount_filter(value):
    if value in (None, ''):
        return None
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise ValueError('Amount filters must be numbers.') from None
    if not number.is_finite():
        raise ValueError('Amount filters must be numbers.')
    return number


def export_transactions(database, authorize=None, account_id=None, start=None, end=None,
                        min_amount=None, max_amount=None, q=None, limit=200):
    path = Path(database).resolve(strict=True)
    limit = int(limit) if str(limit).isdigit() else 200
    if not 1 <= limit <= 1000:
        raise ValueError('Limit must be 1–1000.')
    start, end = _day(start) if start else None, _day(end) if end else None
    low, high = _amount_filter(min_amount), _amount_filter(max_amount)
    if isinstance(q, str):
        q = q.strip()[:100]
    else:
        q = ''
    conn = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=3)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA query_only=ON')
        conn.execute('BEGIN')
        if authorize is not None:
            authorize(conn)
        sql = ("SELECT t.id, t.account_id, a.name AS account_name, a.currency AS currency, t.tx_date, t.description, "
               "t.amount, t.transfer_group, c.name AS category FROM transactions t "
               "JOIN accounts a ON a.id=t.account_id LEFT JOIN categories c ON c.id=t.category_id WHERE 1=1")
        params = []
        if account_id not in (None, ''):
            if not str(account_id).isdigit():
                raise ValueError('account_id must be an integer.')
            sql += ' AND t.account_id=?'
            params.append(int(account_id))
        if start:
            sql += ' AND t.tx_date>=?'
            params.append(start)
        if end:
            sql += ' AND t.tx_date<=?'
            params.append(end)
        if low is not None:
            sql += ' AND t.amount>=?'
            params.append(float(low))
        if high is not None:
            sql += ' AND t.amount<=?'
            params.append(float(high))
        if q:
            sql += ' AND t.description LIKE ? COLLATE NOCASE'
            params.append('%' + q.replace('%', '').replace('_', '') + '%')
        sql += ' ORDER BY t.tx_date DESC, t.id DESC LIMIT ?'
        params.append(limit)
        transactions = []
        for row in conn.execute(sql, params):
            amount = Decimal(str(row['amount']))
            transactions.append(dict(id=row['id'], account_id=row['account_id'], account_name=row['account_name'],
                                     currency=row['currency'], tx_date=row['tx_date'], description=row['description'],
                                     amount=format(amount.quantize(Decimal('.01'), rounding=ROUND_HALF_UP), 'f'),
                                     transfer_group=row['transfer_group'] or '', category=row['category'] or ''))
        return dict(contract=CONTRACT, as_of=datetime.now(timezone.utc).isoformat(), transactions=transactions)
    finally:
        conn.close()


def export_accounts(database, authorize=None):
    path = Path(database).resolve(strict=True)
    conn = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=3)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA query_only=ON')
        conn.execute('BEGIN')
        if authorize is not None:
            authorize(conn)
        accounts = [dict(id=row['id'], name=row['name'], institution=row['institution'] or '',
                         account_type=row['account_type'], currency=row['currency'], active=row['active'])
                    for row in conn.execute('SELECT id,name,institution,account_type,currency,active FROM accounts ORDER BY id LIMIT 2000')]
        return dict(contract=CONTRACT, as_of=datetime.now(timezone.utc).isoformat(), accounts=accounts)
    finally:
        conn.close()


def main():
    try:
        result = export_transactions(Path(__file__).resolve().parents[1] / 'data/finance.db')
        print(json.dumps(result, allow_nan=False))
    except Exception:
        print('Finance Tracker business export unavailable.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
