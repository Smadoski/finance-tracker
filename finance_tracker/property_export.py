"""Read-only, local Property funding contract. No web-app import or startup writes."""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path
import sqlite3
import sys
from .accounts import account_balance

CONTRACT = 'property-funding-v1'


def export_balances(database, authorize=None):
    path = Path(database).resolve(strict=True)
    conn = sqlite3.connect(path.as_uri()+'?mode=ro', uri=True, timeout=3)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA query_only=ON')
        conn.execute('BEGIN')
        if authorize is not None: authorize(conn)
        rows = conn.execute("SELECT * FROM accounts WHERE active=1 AND currency IN ('GBP','EUR') AND account_type NOT IN ('liability','credit_card') ORDER BY id LIMIT 2001").fetchall()
        if len(rows)>2000: raise ValueError('Too many accounts for funding export.')
        accounts=[]
        for row in rows:
            amount=Decimal(str(account_balance(conn,row)))
            if not amount.is_finite(): raise ValueError('Invalid source balance.')
            accounts.append(dict(id=str(row['id']),name=row['name'],institution=row['institution'] or '',
                                 account_type=row['account_type'],currency=row['currency'],
                                 balance=format(amount.quantize(Decimal('.01'),rounding=ROUND_HALF_UP),'f')))
        return dict(contract=CONTRACT,as_of=datetime.now(timezone.utc).isoformat(),accounts=accounts)
    finally:
        conn.close()


def main():
    try:
        result=export_balances(Path(__file__).resolve().parents[1]/'data/finance.db')
        print(json.dumps(result,allow_nan=False))
    except Exception:
        print('Finance Tracker funding export unavailable.',file=sys.stderr)
        return 1
    return 0


if __name__=='__main__':
    raise SystemExit(main())
