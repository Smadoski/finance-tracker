"""Read-only occurrence expansion shared by planning and exports."""
from datetime import date, timedelta
from .recurring import parse_date, next_scheduled_date, adjust_working_day
from .budgets import period_bounds


def window_end(view, today):
    if view=='month': return period_bounds('monthly',today)[1]
    if str(view) not in ('7','30','60','90'): raise ValueError('Choose a supported planning window.')
    return today+timedelta(days=int(view)-1)


def upcoming(conn, start, end, account_ids=None):
    start=parse_date(start); end=parse_date(end)
    if end<start: return []
    rows=[]
    rules=conn.execute('''SELECT r.*,a.name account,a.currency,ta.name destination,ta.currency destination_currency,
        c.name category,p.name parent_category FROM recurring_rules r JOIN accounts a ON a.id=r.account_id
        LEFT JOIN accounts ta ON ta.id=r.to_account_id LEFT JOIN categories c ON c.id=r.category_id
        LEFT JOIN categories p ON p.id=c.parent_id WHERE r.deleted_at IS NULL''').fetchall()
    for rule in rules:
        r=dict(rule)
        if account_ids and r['account_id'] not in account_ids and r['to_account_id'] not in account_ids: continue
        occurrences={o['scheduled_date']:dict(o) for o in conn.execute('SELECT * FROM recurring_occurrences WHERE rule_id=?',(r['id'],))}
        def append(nominal, due, status):
            if start<=due<=end:
                rows.append(dict(rule_id=r['id'],scheduled_date=str(nominal),due_date=str(due),description=r['description'],
                    account_id=r['account_id'],account=r['account'],currency=r['currency'],amount=r['amount'],
                    to_account_id=r['to_account_id'],to_amount=r['to_amount'] or r['amount'],destination=r['destination'],
                    destination_currency=r['destination_currency'],type=r['transaction_type'],category_id=r['category_id'],
                    category=r['parent_category'] or r['category'] or 'Uncategorised',
                    subcategory=r['category'] if r['parent_category'] else '',posting_mode=r['posting_mode'],status=status))
        for occurrence in occurrences.values():
            if occurrence['status']=='pending':
                # Pending entries that were posted outside the recurring screen must not be counted again.
                pending=conn.execute('SELECT id FROM pending_transactions WHERE id=?',(occurrence['pending_id'],)).fetchone() if occurrence['pending_id'] else None
                if not occurrence['pending_id'] or pending:
                    append(parse_date(occurrence['scheduled_date']),parse_date(occurrence['posting_date']),'Pending review')
        if not r['active']: continue
        nominal=parse_date(r['next_scheduled_date'])
        count=0
        while nominal<=end+timedelta(days=14):
            if r['end_date'] and nominal>parse_date(r['end_date']): break
            count+=1
            if count>100000: raise ValueError('Schedule spans too many occurrences; review its next due date.')
            due=adjust_working_day(nominal,r['working_day_adjustment'],r.get('holiday_calendar','weekdays'))
            if str(nominal) not in occurrences: append(nominal,due,'Scheduled')
            nominal=next_scheduled_date(nominal,r['frequency'],r['start_date'])
    return sorted(rows,key=lambda r:(r['due_date'],r['account'],r['description']))
