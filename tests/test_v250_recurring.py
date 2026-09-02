from datetime import date

import pytest

from finance_tracker.recurring import adjust_working_day, next_scheduled_date, process_due


def seed(conn):
    user=conn.execute("INSERT INTO users(name,username,password_hash,role) VALUES('Owner','owner','x','owner')").lastrowid
    a=conn.execute("INSERT INTO accounts(name,account_type,currency) VALUES('Current','bank','GBP')").lastrowid
    b=conn.execute("INSERT INTO accounts(name,account_type,currency) VALUES('Savings','bank','GBP')").lastrowid
    expense=conn.execute("SELECT id FROM categories WHERE kind='expense' ORDER BY id LIMIT 1").fetchone()['id']
    income=conn.execute("SELECT id FROM categories WHERE kind='income' ORDER BY id LIMIT 1").fetchone()['id']
    conn.commit()
    return user,a,b,expense,income


def add_rule(conn, *, user, account, category, start='2024-01-01', frequency='monthly',
             tx_type='expense', mode='automatic', active=1, end=None, to_account=None,
             adjustment='exact', amount=10):
    return conn.execute("""INSERT INTO recurring_rules
        (description,transaction_type,account_id,to_account_id,amount,to_amount,category_id,start_date,end_date,
         next_scheduled_date,frequency,working_day_adjustment,posting_mode,active,created_by)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        ('Scheduled item',tx_type,account,to_account,amount,amount,category,start,end,start,frequency,adjustment,mode,active,user)).lastrowid


@pytest.mark.parametrize(('frequency','expected'),[
    ('weekly',date(2024,1,8)),('monthly',date(2024,2,1)),
    ('quarterly',date(2024,4,1)),('annually',date(2025,1,1)),
])
def test_recurrence_frequencies(frequency,expected):
    assert next_scheduled_date(date(2024,1,1),frequency,date(2024,1,1))==expected


def test_month_end_and_leap_year_handling():
    assert next_scheduled_date(date(2023,1,31),'monthly',date(2023,1,31))==date(2023,2,28)
    assert next_scheduled_date(date(2024,1,31),'monthly',date(2024,1,31))==date(2024,2,29)
    assert next_scheduled_date(date(2024,2,29),'monthly',date(2024,1,31))==date(2024,3,31)
    assert next_scheduled_date(date(2024,3,31),'monthly',date(2024,1,31))==date(2024,4,30)


def test_working_day_adjustments():
    assert adjust_working_day(date(2024,4,20),'previous')==date(2024,4,19)  # Saturday
    assert adjust_working_day(date(2024,10,20),'previous')==date(2024,10,18)  # Sunday
    assert adjust_working_day(date(2024,4,20),'next')==date(2024,4,22)
    assert adjust_working_day(date(2024,4,19),'exact')==date(2024,4,19)


def test_monthly_expense_and_income_are_posted(appmod):
    conn=appmod.db(); user,a,_,expense,income=seed(conn)
    add_rule(conn,user=user,account=a,category=expense,start='2024-01-31')
    add_rule(conn,user=user,account=a,category=income,start='2024-01-31',tx_type='income')
    conn.commit(); process_due(conn,'2024-02-29')
    amounts=[r['amount'] for r in conn.execute('SELECT amount FROM transactions ORDER BY id')]
    assert amounts==[-10,-10,10,10]
    assert conn.execute('SELECT COUNT(*) n FROM recurring_occurrences').fetchone()['n']==4
    conn.close()


def test_paused_end_date_and_skip(appmod):
    conn=appmod.db(); user,a,_,expense,_=seed(conn)
    paused=add_rule(conn,user=user,account=a,category=expense,active=0)
    ended=add_rule(conn,user=user,account=a,category=expense,start='2024-01-01',end='2024-01-01')
    skipped=add_rule(conn,user=user,account=a,category=expense,start='2024-01-01')
    conn.commit()
    from finance_tracker.recurring import advance_rule, process_rule_occurrence
    rule=conn.execute('SELECT * FROM recurring_rules WHERE id=?',(skipped,)).fetchone()
    process_rule_occurrence(conn,rule,rule['next_scheduled_date'],status_override='skipped')
    advance_rule(conn,rule,rule['next_scheduled_date']); conn.commit()
    process_due(conn,'2024-02-01')
    # The ended rule posts its permitted final occurrence; the skipped rule posts February.
    assert conn.execute('SELECT COUNT(*) n FROM transactions').fetchone()['n']==2
    assert conn.execute('SELECT active FROM recurring_rules WHERE id=?',(paused,)).fetchone()['active']==0
    assert conn.execute('SELECT active FROM recurring_rules WHERE id=?',(ended,)).fetchone()['active']==0
    assert conn.execute("SELECT COUNT(*) n FROM recurring_occurrences WHERE rule_id=? AND status='skipped'",(skipped,)).fetchone()['n']==1
    conn.close()


def test_catchup_duplicate_prevention_and_weekend_due_day(appmod):
    conn=appmod.db(); user,a,_,expense,_=seed(conn)
    add_rule(conn,user=user,account=a,category=expense,start='2024-01-01',frequency='weekly')
    add_rule(conn,user=user,account=a,category=expense,start='2024-04-20',adjustment='previous')
    conn.commit(); process_due(conn,'2024-02-01'); process_due(conn,'2024-02-01')
    # Five weekly catch-up occurrences and the Saturday item posted on Friday the 19th.
    process_due(conn,'2024-04-19'); before=conn.execute('SELECT COUNT(*) n FROM transactions').fetchone()['n']
    process_due(conn,'2024-04-19')
    assert conn.execute('SELECT COUNT(*) n FROM transactions').fetchone()['n']==before
    assert conn.execute("SELECT COUNT(*) n FROM transactions WHERE tx_date='2024-04-19'").fetchone()['n']>=1
    conn.close()


def test_pending_and_linked_transfer(appmod):
    conn=appmod.db(); user,a,b,expense,_=seed(conn)
    add_rule(conn,user=user,account=a,category=expense,start='2024-01-01',mode='pending')
    add_rule(conn,user=user,account=a,to_account=b,category=None,start='2024-01-01',tx_type='transfer')
    conn.commit(); process_due(conn,'2024-01-01')
    assert conn.execute('SELECT COUNT(*) n FROM pending_transactions').fetchone()['n']==1
    legs=conn.execute('SELECT * FROM transactions ORDER BY id').fetchall()
    assert len(legs)==2 and legs[0]['transfer_group']==legs[1]['transfer_group']
    assert legs[0]['amount']==-legs[1]['amount']
    conn.close()
