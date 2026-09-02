"""Recurring transaction scheduling and idempotent occurrence processing."""

import calendar
import secrets
import threading
import time
from datetime import date, datetime, timedelta

from .database import connect


FREQUENCIES={'daily','weekly','monthly','quarterly','annually'}
ADJUSTMENTS={'exact','previous','next'}
POSTING_MODES={'automatic','pending'}


def parse_date(value):
    return value if isinstance(value,date) else date.fromisoformat(str(value))


def month_shift(value, months, anchor_day):
    value=parse_date(value)
    month_index=value.year*12+(value.month-1)+months
    year,month=divmod(month_index,12)
    month+=1
    return date(year,month,min(int(anchor_day),calendar.monthrange(year,month)[1]))


def next_scheduled_date(current, frequency, start_date):
    current=parse_date(current); start=parse_date(start_date)
    if frequency=='daily': return current+timedelta(days=1)
    if frequency=='weekly': return current+timedelta(days=7)
    if frequency=='monthly': return month_shift(current,1,start.day)
    if frequency=='quarterly': return month_shift(current,3,start.day)
    if frequency=='annually': return month_shift(current,12,start.day)
    raise ValueError('Unsupported recurring frequency.')


def adjust_working_day(value, adjustment):
    value=parse_date(value)
    if adjustment=='exact': return value
    if adjustment=='previous':
        while value.weekday()>=5: value-=timedelta(days=1)
        return value
    if adjustment=='next':
        while value.weekday()>=5: value+=timedelta(days=1)
        return value
    raise ValueError('Unsupported working-day adjustment.')


def validate_rule(conn, data):
    tx_type=data['transaction_type']; frequency=data['frequency']; adjustment=data['working_day_adjustment']; mode=data['posting_mode']
    if tx_type not in ('expense','income','transfer'): raise ValueError('Choose a valid transaction type.')
    if frequency not in FREQUENCIES or adjustment not in ADJUSTMENTS or mode not in POSTING_MODES: raise ValueError('Choose valid scheduling options.')
    amount=abs(float(data['amount']))
    if amount<=0: raise ValueError('Amount must be greater than zero.')
    account_id=int(data['account_id'])
    account=conn.execute("SELECT * FROM accounts WHERE id=? AND active=1 AND account_type NOT IN ('pension','other_asset','liability')",(account_id,)).fetchone()
    if not account: raise ValueError('Choose a valid active account.')
    to_account_id=int(data['to_account_id']) if data.get('to_account_id') else None
    to_amount=abs(float(data.get('to_amount') or amount))
    if tx_type=='transfer':
        target=conn.execute("SELECT * FROM accounts WHERE id=? AND active=1 AND account_type NOT IN ('pension','other_asset','liability')",(to_account_id,)).fetchone() if to_account_id else None
        if not target or to_account_id==account_id: raise ValueError('Choose two different active accounts for the transfer.')
        if to_amount<=0: raise ValueError('Transfer amounts must be greater than zero.')
    else:
        to_account_id=None; to_amount=None
    category_id=int(data['category_id']) if data.get('category_id') else None
    if category_id:
        category=conn.execute('SELECT * FROM categories WHERE id=?',(category_id,)).fetchone()
        if not category or category['kind']!=tx_type: raise ValueError('Choose a category matching the transaction type.')
    start=parse_date(data['start_date']); end=parse_date(data['end_date']) if data.get('end_date') else None
    if end and end<start: raise ValueError('End date cannot be before start date.')
    return dict(description=(data.get('description') or '').strip(),transaction_type=tx_type,account_id=account_id,to_account_id=to_account_id,
                amount=amount,to_amount=to_amount,category_id=category_id,start_date=start.isoformat(),end_date=end.isoformat() if end else None,
                next_scheduled_date=(parse_date(data.get('next_scheduled_date') or start)).isoformat(),frequency=frequency,
                working_day_adjustment=adjustment,posting_mode=mode,active=1 if data.get('active',True) else 0)


def _post_occurrence(conn, rule, scheduled, posting, force_post=False):
    posting_mode='automatic' if force_post else rule['posting_mode']
    tx_type=rule['transaction_type']; user_id=rule['created_by']; description=rule['description']
    if tx_type=='transfer' and posting_mode=='pending':
        return ('pending',None,None,None,'Transfer awaiting review')
    if tx_type=='transfer':
        source=conn.execute('SELECT name FROM accounts WHERE id=?',(rule['account_id'],)).fetchone()
        target=conn.execute('SELECT name FROM accounts WHERE id=?',(rule['to_account_id'],)).fetchone()
        if not source or not target: raise ValueError('Scheduled transfer account is unavailable.')
        category=conn.execute("SELECT id FROM categories WHERE name='Transfer'").fetchone(); category_id=category['id'] if category else None
        group=secrets.token_hex(8)
        first=conn.execute('INSERT INTO transactions(account_id,tx_date,description,amount,category_id,tag_text,notes,transfer_group,created_by) VALUES(?,?,?,?,?,?,?,?,?)',
            (rule['account_id'],posting,description,-abs(float(rule['amount'])),category_id,'Scheduled Transfer',f'Transfer to {target["name"]}',group,user_id)).lastrowid
        conn.execute('INSERT INTO transactions(account_id,tx_date,description,amount,category_id,tag_text,notes,transfer_group,created_by) VALUES(?,?,?,?,?,?,?,?,?)',
            (rule['to_account_id'],posting,description,abs(float(rule['to_amount'] or rule['amount'])),category_id,'Scheduled Transfer',f'Transfer from {source["name"]}',group,user_id))
        return ('posted',first,None,group,'Linked transfer posted')
    amount=abs(float(rule['amount']))*(-1 if tx_type=='expense' else 1)
    if posting_mode=='pending':
        pending_id=conn.execute('INSERT INTO pending_transactions(account_id,tx_date,description,amount,category_id,entry_type,notes,created_by) VALUES(?,?,?,?,?,?,?,?)',
            (rule['account_id'],posting,description,amount,rule['category_id'],tx_type,'Created by recurring schedule',user_id)).lastrowid
        return ('pending',None,pending_id,None,'Created as Pending for review')
    transaction_id=conn.execute('INSERT INTO transactions(account_id,tx_date,description,amount,category_id,tag_text,notes,created_by) VALUES(?,?,?,?,?,?,?,?)',
        (rule['account_id'],posting,description,amount,rule['category_id'],'Scheduled','Created by recurring schedule',user_id)).lastrowid
    return ('posted',transaction_id,None,None,'Posted automatically')


def process_rule_occurrence(conn, rule, scheduled_date, status_override=None, force_post=False):
    scheduled=parse_date(scheduled_date); posting=adjust_working_day(scheduled,rule['working_day_adjustment'])
    existing=conn.execute('SELECT * FROM recurring_occurrences WHERE rule_id=? AND scheduled_date=?',(rule['id'],scheduled.isoformat())).fetchone()
    if existing: return existing
    if status_override=='skipped':
        values=('skipped',None,None,None,'Skipped by user')
    else:
        values=_post_occurrence(conn,rule,scheduled.isoformat(),posting.isoformat(),force_post=force_post)
    status,transaction_id,pending_id,group,detail=values
    conn.execute('INSERT INTO recurring_occurrences(rule_id,scheduled_date,posting_date,status,transaction_id,pending_id,transfer_group,detail) VALUES(?,?,?,?,?,?,?,?)',
        (rule['id'],scheduled.isoformat(),posting.isoformat(),status,transaction_id,pending_id,group,detail))
    return conn.execute('SELECT * FROM recurring_occurrences WHERE rule_id=? AND scheduled_date=?',(rule['id'],scheduled.isoformat())).fetchone()


def advance_rule(conn, rule, scheduled):
    next_date=next_scheduled_date(scheduled,rule['frequency'],rule['start_date'])
    active=0 if rule['end_date'] and next_date>parse_date(rule['end_date']) else int(rule['active'])
    conn.execute('UPDATE recurring_rules SET next_scheduled_date=?,active=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(next_date.isoformat(),active,rule['id']))
    return next_date


def post_pending_transfer(conn, occurrence_id):
    occurrence=conn.execute("SELECT * FROM recurring_occurrences WHERE id=? AND status='pending' AND pending_id IS NULL",(occurrence_id,)).fetchone()
    if not occurrence: raise ValueError('Pending scheduled transfer was not found.')
    rule=conn.execute('SELECT * FROM recurring_rules WHERE id=?',(occurrence['rule_id'],)).fetchone()
    if not rule or rule['transaction_type']!='transfer': raise ValueError('Occurrence is not a scheduled transfer.')
    status,transaction_id,pending_id,group,detail=_post_occurrence(conn,rule,occurrence['scheduled_date'],occurrence['posting_date'],force_post=True)
    conn.execute('UPDATE recurring_occurrences SET status=?,transaction_id=?,pending_id=?,transfer_group=?,detail=? WHERE id=?',
                 (status,transaction_id,pending_id,group,detail,occurrence_id))
    conn.commit()
    return conn.execute('SELECT * FROM recurring_occurrences WHERE id=?',(occurrence_id,)).fetchone()


def process_due(conn, today=None, max_occurrences=1000):
    today=parse_date(today or date.today()); processed=[]; count=0
    conn.execute('BEGIN IMMEDIATE')
    try:
        rules=conn.execute('SELECT * FROM recurring_rules WHERE active=1 AND deleted_at IS NULL ORDER BY id').fetchall()
        for original in rules:
            rule=original
            scheduled=parse_date(rule['next_scheduled_date'])
            while adjust_working_day(scheduled,rule['working_day_adjustment'])<=today and count<max_occurrences:
                if rule['end_date'] and scheduled>parse_date(rule['end_date']):
                    conn.execute('UPDATE recurring_rules SET active=0 WHERE id=?',(rule['id'],)); break
                processed.append(process_rule_occurrence(conn,rule,scheduled)); count+=1
                scheduled=advance_rule(conn,rule,scheduled)
                rule=conn.execute('SELECT * FROM recurring_rules WHERE id=?',(rule['id'],)).fetchone()
                if not rule['active']: break
        conn.commit()
    except Exception:
        conn.rollback(); raise
    return processed


def process_due_path(db_path, today=None):
    conn=connect(db_path)
    try: return process_due(conn,today=today)
    finally: conn.close()


def start_scheduler(db_path, interval_seconds=300, stop_event=None):
    stop_event=stop_event or threading.Event()
    def run():
        while not stop_event.is_set():
            try: process_due_path(db_path)
            except Exception: pass
            stop_event.wait(interval_seconds)
    thread=threading.Thread(target=run,name='finance-recurring-scheduler',daemon=True); thread.start()
    return thread,stop_event
