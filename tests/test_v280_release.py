import sqlite3
from datetime import date
from decimal import Decimal
import pytest
from finance_tracker.recurring import process_rule_occurrence

@pytest.fixture
def records(appmod):
    appmod.set_setting('auth_required','0'); appmod.set_setting('tailnet_only','0')
    conn=appmod.db()
    a=conn.execute("INSERT INTO accounts(name,account_type,currency) VALUES('Test Current','current','EUR')").lastrowid
    b=conn.execute("INSERT INTO accounts(name,account_type,currency) VALUES('Test GBP','savings','GBP')").lastrowid
    category=conn.execute("SELECT id FROM categories WHERE kind='expense' LIMIT 1").fetchone()[0]
    rule=conn.execute("""INSERT INTO recurring_rules(description,transaction_type,account_id,amount,category_id,start_date,next_scheduled_date,frequency,posting_mode)
        VALUES('Four-weekly bill','expense',?,100,?,'2026-01-01','2026-01-01','monthly','automatic')""",(a,category)).lastrowid
    conn.commit()
    client=appmod.app.test_client()
    with client.session_transaction() as s:s['csrf']='test'
    yield appmod,conn,client,a,b,category,rule
    conn.close()


def test_delete_recurring_transaction_regression(records):
    app,conn,client,a,b,category,rule_id=records
    rule=conn.execute('SELECT * FROM recurring_rules WHERE id=?',(rule_id,)).fetchone()
    occurrence=process_rule_occurrence(conn,rule,'2026-01-01'); conn.commit()
    response=client.post(f'/transaction/{occurrence["transaction_id"]}/delete',data={'_csrf':'test'})
    assert response.status_code==302
    assert conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]==0
    audit=conn.execute('SELECT * FROM recurring_occurrences').fetchone()
    assert audit['transaction_id'] is None and audit['status']=='posted'
    assert not conn.execute('PRAGMA foreign_key_check').fetchall()

from finance_tracker.recurring import next_scheduled_date, validate_rule
from finance_tracker.frequencies import equivalents
from finance_tracker.recurring_report import recurring_report, export_columns
from finance_tracker.migrations import migrate_v280

@pytest.mark.parametrize('frequency,current,start,expected',[
 ('daily','2026-01-01','2026-01-01','2026-01-02'),('weekly','2026-01-01','2026-01-01','2026-01-08'),
 ('fortnightly','2026-01-01','2026-01-01','2026-01-15'),('four_weekly','2026-01-01','2026-01-01','2026-01-29'),
 ('monthly','2026-01-31','2026-01-31','2026-02-28'),('quarterly','2026-01-31','2026-01-31','2026-04-30'),
 ('six_monthly','2026-01-31','2026-01-31','2026-07-31'),('annually','2024-02-29','2024-02-29','2025-02-28'),
 ('first_day','2026-01-01','2026-01-01','2026-02-01'),('first_day','2026-12-01','2026-12-01','2027-01-01'),
 ('last_day','2026-01-31','2026-01-31','2026-02-28'),('last_day','2024-01-31','2024-01-31','2024-02-29'),
 ('last_day','2026-03-31','2026-01-31','2026-04-30'),('last_day','2026-04-30','2026-01-31','2026-05-31'),
 ('last_day','2026-12-31','2026-01-31','2027-01-31')])
def test_recurrence(frequency,current,start,expected):
    assert str(next_scheduled_date(current,frequency,start))==expected


def test_thirteen_four_weekly_payments_per_52_weeks():
    from datetime import timedelta
    start=date(2026,1,1); current=start; payments=[]
    while current<start+timedelta(weeks=52):
        payments.append(current);current=next_scheduled_date(current,'four_weekly',start)
    assert len(payments)==13 and current==start+timedelta(weeks=52)
    assert all((b-a).days==28 for a,b in zip(payments,payments[1:]))

@pytest.mark.parametrize('frequency,amount,annual,monthly',[
 ('four_weekly','100','1300','108.33'),('annually','1200','1200','100.00'),('quarterly','300','1200','100.00'),
 ('six_monthly','600','1200','100.00'),('monthly','100','1200','100.00'),('first_day','100','1200','100.00'),
 ('last_day','100','1200','100.00'),('weekly','10','520','43.33'),('fortnightly','10','260','21.67'),('daily','1','365','30.42')])
def test_decimal_normalisation(frequency,amount,annual,monthly):
    m,a=equivalents(amount,frequency)
    assert isinstance(m,Decimal) and a==Decimal(annual) and format(m,'.2f')==monthly

@pytest.mark.parametrize('frequency,expected',[('first_day','2026-02-01'),('last_day','2026-01-31')])
def test_new_rule_initial_alignment(records,frequency,expected):
    _,conn,_,a,_,category,_=records
    rule=validate_rule(conn,dict(transaction_type='expense',frequency=frequency,working_day_adjustment='exact',posting_mode='automatic',amount='100',account_id=a,category_id=category,start_date='2026-01-15'))
    assert rule['next_scheduled_date']==expected


def test_report_filtered_totals_and_multi_currency(records):
    _,conn,_,a,b,cat,rule=records
    conn.execute("UPDATE recurring_rules SET frequency='four_weekly' WHERE id=?",(rule,))
    conn.execute("""INSERT INTO recurring_rules(description,transaction_type,account_id,amount,category_id,start_date,next_scheduled_date,frequency,posting_mode,active)
    VALUES('Inactive GBP','expense',?,100,?,'2026-01-01','2026-01-01','annually','automatic',0)""",(b,cat))
    filters=dict(category_id=str(cat),account_id=str(a),currency='EUR',frequency='four_weekly',status='active',monthly='1',annual='1')
    r=recurring_report(conn,filters,'EUR',1.2)
    assert len(r['rows'])==1 and r['groups'][0]['amount']==100
    assert r['totals']['expense']['annual']==1300
    assert format(r['totals']['expense']['monthly'],'.2f')=='108.33'
    all_rows=recurring_report(conn,{},'EUR',1.2)
    assert all_rows['totals']['expense']['annual']==1420
    assert len(all_rows['groups'])==2
    assert len(recurring_report(conn,{'status':'inactive'},'GBP',1.2)['rows'])==1
    assert recurring_report(conn,dict(filters,currency='GBP'),'EUR',1.2)['rows']==[]

@pytest.mark.parametrize('key,value',[('account_id','999999'),('category_id','999999'),('currency','GBP'),('frequency','daily'),('status','inactive')])
def test_each_report_filter(records,key,value):
    assert not recurring_report(records[1],{key:value},'EUR',1.2)['rows']

@pytest.mark.parametrize('options', [{},{'monthly':'1'},{'annual':'1'},{'monthly':'1','annual':'1'}])
def test_report_html_csv_pdf_options(records,options):
    _,conn,client,_,_,_,rule=records
    conn.execute("UPDATE recurring_rules SET frequency='four_weekly' WHERE id=?",(rule,));conn.commit()
    html=client.get('/reports/recurring',query_string=options)
    assert html.status_code==200 and b'Every 4 weeks' in html.data
    assert (b'108.33/month equivalent' in html.data)==('monthly' in options)
    csv=client.get('/reports/recurring',query_string=dict(options,format='csv'))
    assert csv.status_code==200 and b'100.00,EUR,Every 4 weeks' in csv.data
    assert (b'Monthly equivalent' in csv.data)==('monthly' in options)
    assert (b'Annual equivalent' in csv.data)==('annual' in options)
    pdf=client.get('/reports/recurring',query_string=dict(options,format='pdf',share='1'))
    assert pdf.status_code==200 and pdf.data.startswith(b'%PDF') and pdf.headers['Content-Disposition'].startswith('inline')


def test_report_exports_apply_filters(records):
    _,_,client,a,*_=records
    for fmt in ['html','csv','pdf']:
        response=client.get('/reports/recurring',query_string=dict(format=fmt,account_id=a,currency='GBP',monthly='1'))
        assert response.status_code==200
        if fmt!='pdf': assert b'Four-weekly bill' not in response.data


def test_normal_delete_shared_receipt_and_transfer(records,tmp_path):
    app,conn,client,a,b,cat,rule=records
    receipt='shared.png'; path=__import__('pathlib').Path(app.RECEIPT_DIR)/receipt;path.write_bytes(b'test receipt')
    ids=[]
    for account,group in [(a,None),(a,'linked'),(b,'linked'),(a,None)]:
        ids.append(conn.execute('INSERT INTO transactions(account_id,tx_date,description,amount,transfer_group,receipt_path) VALUES(?,?,?,?,?,?)',(account,'2026-01-01','Delete test',10,group,receipt)).lastrowid)
    conn.commit()
    assert client.post(f'/transaction/{ids[0]}/delete',data={'_csrf':'test'}).status_code==302
    assert path.exists()
    assert client.post(f'/transaction/{ids[1]}/delete',data={'_csrf':'test'}).status_code==302
    assert [r[0] for r in conn.execute('SELECT id FROM transactions')]==[ids[3]] and path.exists()
    client.post(f'/transaction/{ids[3]}/delete',data={'_csrf':'test'})
    assert not path.exists()
    assert client.post(f'/transaction/{ids[3]}/delete',data={'_csrf':'test'}).status_code==404


def test_delete_rolls_back_audit_and_financial_changes(records):
    from finance_tracker.transactions import delete_transaction_atomic
    _,conn,_,_,_,_,rule_id=records
    occurrence=process_rule_occurrence(conn,conn.execute('SELECT * FROM recurring_rules WHERE id=?',(rule_id,)).fetchone(),'2026-01-01');conn.commit()
    conn.execute("CREATE TRIGGER refuse_delete BEFORE DELETE ON transactions BEGIN SELECT RAISE(ABORT,'test failure'); END");conn.commit()
    with pytest.raises(sqlite3.IntegrityError):delete_transaction_atomic(conn,occurrence['transaction_id'])
    assert conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]==1
    assert conn.execute('SELECT transaction_id FROM recurring_occurrences').fetchone()[0]==occurrence['transaction_id']


def test_recurring_transfer_delete_from_credit_leg(records):
    _,conn,client,a,b,cat,rule_id=records
    conn.execute("UPDATE recurring_rules SET transaction_type='transfer',to_account_id=?,to_amount=80,category_id=NULL WHERE id=?",(b,rule_id))
    occurrence=process_rule_occurrence(conn,conn.execute('SELECT * FROM recurring_rules WHERE id=?',(rule_id,)).fetchone(),'2026-01-01');conn.commit()
    credit=conn.execute('SELECT id FROM transactions WHERE account_id=?',(b,)).fetchone()[0]
    assert client.post(f'/transaction/{credit}/delete',data={'_csrf':'test'}).status_code==302
    assert conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]==0
    assert conn.execute('SELECT transaction_id FROM recurring_occurrences').fetchone()[0] is None


def test_migration_preserves_rules_occurrences_and_rolls_back_on_failure(records,tmp_path):
    _,conn,*_=records
    original=[tuple(r) for r in conn.execute('SELECT * FROM recurring_rules')]
    migrate_v280(conn);migrate_v280(conn)
    assert original==[tuple(r) for r in conn.execute('SELECT * FROM recurring_rules')]
    assert not conn.execute('PRAGMA foreign_key_check').fetchall()
    assert conn.execute('PRAGMA quick_check').fetchone()[0]=='ok'
    # Reconstruct the released CHECK constraint on an isolated schema, then deny DROP to force failure.
    old=sqlite3.connect(tmp_path/'old.db');old.row_factory=sqlite3.Row
    schema=conn.execute("SELECT sql FROM sqlite_master WHERE name='recurring_rules'").fetchone()[0]
    from finance_tracker.frequencies import FREQUENCY_LABELS
    import re
    schema=re.sub(r'frequency IN \([^)]*\)',"frequency IN ('daily','weekly','monthly','quarterly','annually')",schema)
    old.execute(schema);old.execute('CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT)');old.commit()
    old.set_authorizer(lambda action,*args: sqlite3.SQLITE_DENY if action==sqlite3.SQLITE_DROP_TABLE else sqlite3.SQLITE_OK)
    with pytest.raises(sqlite3.DatabaseError):migrate_v280(old)
    old.set_authorizer(None)
    assert old.execute("SELECT sql FROM sqlite_master WHERE name='recurring_rules'").fetchone()[0]==schema
    assert not old.execute("SELECT 1 FROM sqlite_master WHERE name='recurring_rules_v280'").fetchone()
    old.close()

@pytest.mark.parametrize('path',['/reports/recurring?format=pdf','/reports/recurring?format=csv','/report/net-worth.pdf?share=1'])
def test_exports_preserve_authentication_and_tailnet(records,path):
    app,_,client,*_=records
    app.set_setting('auth_required','1')
    assert client.get(path).status_code==302
    app.set_setting('auth_required','0');app.set_setting('tailnet_only','1')
    assert client.get(path,environ_overrides={'REMOTE_ADDR':'192.0.2.1'}).status_code==403

@pytest.mark.parametrize('frequency,start,next_date',[('four_weekly','2026-01-01','2026-01-29'),('first_day','2026-02-01','2026-03-01'),('last_day','2024-02-29','2024-03-31')])
def test_new_frequencies_post_and_advance(records,frequency,start,next_date):
    from finance_tracker.recurring import process_due
    _,conn,_,_,_,_,rule=records
    conn.execute('UPDATE recurring_rules SET frequency=?,start_date=?,next_scheduled_date=? WHERE id=?',(frequency,start,start,rule));conn.commit()
    process_due(conn,start);process_due(conn,start)
    assert conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]==1
    assert conn.execute('SELECT next_scheduled_date FROM recurring_rules WHERE id=?',(rule,)).fetchone()[0]==next_date


def test_readonly_delete_blocked(records):
    app,conn,client,a,*_=records
    user=conn.execute("INSERT INTO users(name,username,password_hash,role) VALUES('Read Only','readonly270','x','readonly')").lastrowid
    tx=conn.execute("INSERT INTO transactions(account_id,tx_date,description,amount) VALUES(?,'2026-01-01','Keep',-10)",(a,)).lastrowid;conn.commit()
    app.set_setting('auth_required','1')
    with client.session_transaction() as s:s.update(user_id=user,auth_version=1,csrf='test')
    assert client.post(f'/transaction/{tx}/delete',data={'_csrf':'test'}).status_code==403
    assert conn.execute('SELECT id FROM transactions WHERE id=?',(tx,)).fetchone()

@pytest.mark.parametrize('frequency',['four_weekly','first_day','last_day','fortnightly','six_monthly'])
def test_new_schedules_keep_planning_and_holiday_calendars(records,frequency):
    from finance_tracker.upcoming import upcoming
    from finance_tracker.forecasting import forecast
    from finance_tracker.target_projection import projected_targets
    _,conn,_,account,_,category,rule_id=records
    values=validate_rule(conn,dict(description='Calendar integration',transaction_type='expense',frequency=frequency,
        working_day_adjustment='previous',holiday_calendar='uk',posting_mode='automatic',amount='100',account_id=account,
        category_id=category,start_date='2026-05-01'))
    columns=','.join(k+'=?' for k in values)
    conn.execute('UPDATE recurring_rules SET '+columns+' WHERE id=?',[*values.values(),rule_id])
    conn.execute("INSERT INTO category_targets(category_id,target_amount,currency,period) VALUES(?,500,'EUR','monthly')",(category,))
    conn.commit()
    items=upcoming(conn,date(2026,4,30),date(2026,5,31))
    report=recurring_report(conn,{},'EUR',1.2)
    assert report['rows'][0]['next_payment']==items[0]['due_date']
    assert report['rows'][0]['holiday_calendar']=='uk'
    f=forecast(conn,date(2026,5,1),date(2026,5,31),'EUR',1.2)
    may_items=[i for i in items if i['due_date']>='2026-05-01']
    assert f['expense']==100*len(may_items)
    targets=projected_targets(conn,'monthly',date(2026,5,1),'EUR',1.2,today=date(2026,5,1))
    assert targets['projected']==f['expense']


def test_original_v270_schema_migrates_with_calendars_and_audit(records,tmp_path):
    import re
    _,conn,_,_,_,_,rule_id=records
    conn.execute("UPDATE recurring_rules SET holiday_calendar='cyprus' WHERE id=?",(rule_id,))
    process_rule_occurrence(conn,conn.execute('SELECT * FROM recurring_rules WHERE id=?',(rule_id,)).fetchone(),'2026-01-01');conn.commit()
    dump='\n'.join(conn.iterdump())
    dump=re.sub(r'frequency IN \([^)]*\)',"frequency IN ('daily','weekly','monthly','quarterly','annually')",dump)
    old=sqlite3.connect(tmp_path/'original270.db');old.row_factory=sqlite3.Row;old.executescript(dump);old.execute('PRAGMA foreign_keys=ON')
    old.execute('CREATE INDEX custom_rule_description ON recurring_rules(description)')
    old.execute("UPDATE sqlite_sequence SET seq=999 WHERE name='recurring_rules'");old.commit()
    tables=('accounts','transactions','recurring_rules','recurring_occurrences','category_targets','csv_import_batches')
    before={name:[tuple(r) for r in old.execute('SELECT * FROM '+name)] for name in tables}
    migrate_v280(old);migrate_v280(old)
    assert before=={name:[tuple(r) for r in old.execute('SELECT * FROM '+name)] for name in tables}
    assert old.execute("SELECT seq FROM sqlite_sequence WHERE name='recurring_rules'").fetchone()[0]==999
    assert old.execute("SELECT 1 FROM sqlite_master WHERE name='custom_rule_description'").fetchone()
    assert not old.execute('PRAGMA foreign_key_check').fetchall()
    assert old.execute('PRAGMA foreign_keys').fetchone()[0]==1
    old.execute("UPDATE recurring_rules SET frequency='four_weekly' WHERE id=?",(rule_id,));old.commit();old.close()
