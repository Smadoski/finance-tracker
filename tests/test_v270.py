import io
import json
import re
import sqlite3
from datetime import date
import pytest
from finance_tracker.recurring import adjust_working_day, process_rule_occurrence, process_due
from finance_tracker.upcoming import upcoming, window_end
from finance_tracker.forecasting import forecast
from finance_tracker.target_projection import projected_targets
from finance_tracker.budgets import target_report
from finance_tracker.search import search_transactions
from finance_tracker.csv_io import parse_csv, preview_import, import_reviewed, export_transactions
from finance_tracker.ai_review import financial_review
from finance_tracker.migrations import migrate_v270

TODAY=date(2026,9,9)

@pytest.fixture
def finance(appmod):
    conn=appmod.db()
    user=conn.execute("INSERT INTO users(name,username,password_hash,role) VALUES('Reviewer','reviewer','secret-hash','admin')").lastrowid
    a=conn.execute("INSERT INTO accounts(name,account_type,currency,opening_balance) VALUES('Current','current','GBP',1000)").lastrowid
    b=conn.execute("INSERT INTO accounts(name,account_type,currency,opening_balance) VALUES('Euro','savings','EUR',120)").lastrowid
    parent=conn.execute("INSERT INTO categories(name,kind) VALUES('Test Household','expense')").lastrowid
    child=conn.execute("INSERT INTO categories(name,kind,parent_id) VALUES('Test Groceries','expense',?)",(parent,)).lastrowid
    income=conn.execute("SELECT id FROM categories WHERE kind='income' LIMIT 1").fetchone()[0]
    conn.execute('INSERT INTO transactions(account_id,tx_date,description,amount,category_id,created_by) VALUES(?,?,?,?,?,?)',(a,'2026-09-05','Merchant shop',-50,child,user))
    conn.execute("INSERT INTO category_targets(category_id,target_amount,currency,period) VALUES(?,500,'GBP','monthly')",(parent,))
    conn.execute("INSERT INTO category_targets(category_id,target_amount,currency,period) VALUES(?,100,'GBP','monthly')",(child,))
    for kind,amount,cat,destination in [('income',200,income,None),('expense',60,child,None),('transfer',20,None,b)]:
        conn.execute('''INSERT INTO recurring_rules(description,transaction_type,account_id,to_account_id,amount,to_amount,category_id,start_date,next_scheduled_date,frequency,posting_mode,created_by)
        VALUES(?,?,?,?,?,?,?,'2026-09-10','2026-09-10','monthly','automatic',?)''',(kind,kind,a,destination,amount,24 if destination else None,cat,user))
    conn.commit()
    yield appmod,conn,user,a,b,parent,child
    conn.close()

@pytest.mark.parametrize('value,rule,calendar,expected',[
 ('2026-09-20','previous','weekdays','2026-09-18'),('2026-09-20','next','weekdays','2026-09-21'),
 ('2026-04-06','previous','uk','2026-04-02'),('2026-12-26','next','uk','2026-12-29'),
 ('2026-04-14','previous','cyprus','2026-04-09'),('2026-01-06','next','cyprus','2026-01-07'),
 ('2026-04-06','exact','uk','2026-04-06'),('2026-04-12','exact','cyprus','2026-04-12')])
def test_holidays(value,rule,calendar,expected):
    assert str(adjust_working_day(value,rule,calendar))==expected

@pytest.mark.parametrize('view,count',[('7',3),('30',3),('month',3)])
def test_upcoming_windows(finance,view,count):
    _,conn,*_=finance
    assert len(upcoming(conn,TODAY,window_end(view,TODAY)))==count

@pytest.mark.parametrize('status',['posted','skipped','pending'])
def test_occurrence_not_double_counted(finance,status):
    _,conn,*_=finance
    rule=conn.execute("SELECT * FROM recurring_rules WHERE transaction_type='expense'").fetchone()
    if status=='pending':
        conn.execute("UPDATE recurring_rules SET posting_mode='pending' WHERE id=?",(rule['id'],))
        rule=conn.execute('SELECT * FROM recurring_rules WHERE id=?',(rule['id'],)).fetchone()
    process_rule_occurrence(conn,rule,'2026-09-10',status_override='skipped' if status=='skipped' else None)
    rows=[r for r in upcoming(conn,TODAY,date(2026,9,30)) if r['type']=='expense']
    assert len(rows)==(1 if status=='pending' else 0)
    if status=='pending':
        from finance_tracker.recurring import resolve_pending_occurrence
        pid=conn.execute('SELECT id FROM pending_transactions').fetchone()[0]
        resolve_pending_occurrence(conn,pid)
        conn.execute('DELETE FROM pending_transactions')
        assert not [r for r in upcoming(conn,TODAY,date(2026,9,30)) if r['type']=='expense']

@pytest.mark.parametrize('view,count',[('30',1),('60',2),('90',3)])
def test_forecast_windows_and_transfer_conversion(finance,view,count):
    _,conn,_,a,b,*_=finance
    before=list(conn.iterdump())
    result=forecast(conn,TODAY,window_end(view,TODAY),'GBP',1.2)
    assert result['current']==1050
    assert result['income']==200*count
    assert result['expense']==60*count
    assert result['transfers']==pytest.approx(0)
    assert result['projected']==pytest.approx(1050+140*count)
    assert result['accounts'][0]['projected']==950+120*count
    assert list(conn.iterdump())==before

@pytest.mark.parametrize('selection,expected',[(0,-20),(1,20)])
def test_filtered_transfer_leg(finance,selection,expected):
    _,conn,_,a,b,*_=finance
    result=forecast(conn,TODAY,date(2026,9,30),'GBP',1.2,[a,b][selection:selection+1])
    assert result['transfers']==expected

@pytest.mark.parametrize('actual,status',[(50,'Under target'),(120,'Over target')])
def test_targets_preserve_actuals_and_project(finance,actual,status):
    _,conn,_,a,b,parent,child=finance
    conn.execute('UPDATE transactions SET amount=?',(-actual,))
    old=target_report(conn,'monthly',TODAY,'GBP',1.2)
    new=projected_targets(conn,'monthly',TODAY,'GBP',1.2,today=TODAY)
    assert new['actual']==old['actual']==actual
    assert new['target']==100 and len(new['rows'])==2
    assert new['projected']==actual+60
    assert new['status']==status
    row=next(r for r in new['rows'] if r['category_id']==child)
    assert row['projection_status']==('Likely to exceed target' if actual==50 else 'Over target')

@pytest.mark.parametrize('filters,expected',[
 ({'q':'merchant'},1),({'q':'missing'},0),({'start':'2026-09-06'},0),({'end':'2026-09-05'},1),
 ({'min_amount':'-60','max_amount':'-40'},1),({'min_amount':'0'},0),({'type':'expense'},1),({'type':'income'},0),
 ({'q':'Merchant','start':'2026-09-01','end':'2026-09-30','min_amount':'-50','max_amount':'-50','type':'expense'},1),
 ({'q':"' OR 1=1 --"},0),({'q':'%'},0)])
def test_search_filters(finance,filters,expected):
    assert len(search_transactions(finance[1],filters))==expected

@pytest.mark.parametrize('key,index',[('account_id',3),('category_id',5),('subcategory_id',6),('user_id',2)])
def test_search_relational_filters(finance,key,index):
    assert len(search_transactions(finance[1],{key:str(finance[index])}))==1
    assert search_transactions(finance[1],{key:'999999'})==[]

def test_csv_export_allowlist_and_escaping(finance):
    rows=search_transactions(finance[1],{})
    rows[0]['description']='=1+1'
    value=export_transactions(rows,'EUR',1.2)
    assert "'=1+1" in value and '-60.0' in value
    assert 'secret-hash' not in value and 'receipt' not in value and 'Equivalent currency' in value

@pytest.fixture
def source():
    return parse_csv(b'Date,Description,Amount,Currency\n2026-09-05,Merchant shop,-50,GBP\n2026-09-06,New,-10,GBP\ninvalid,Bad,nan,GBP\n')

@pytest.mark.parametrize('duplicates,imported,skipped',[(set(),1,1),({'1'},2,0)])
def test_csv_preview_mapping_duplicate_review_and_summary(finance,source,duplicates,imported,skipped):
    _,conn,user,a,*_=finance
    before=conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]
    rows=preview_import(conn,source,dict(date='Date',description='Description',amount='Amount',currency='Currency'),a)
    assert rows[0]['duplicate'] and rows[2]['error']
    assert conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]==before
    result=import_reviewed(conn,rows,{'1','2'},duplicates,user)
    assert result==dict(imported=imported,skipped=skipped,duplicates=1,failed=1)

def test_debit_credit_mapping_and_infile_duplicates(finance):
    source=parse_csv(b'day,text,out,in\n10/09/2026,Coffee,4,\n10/09/2026,Coffee,4,\n11/09/2026,Income,,20\n')
    rows=preview_import(finance[1],source,dict(date='day',description='text',debit='out',credit='in'),finance[3],'%d/%m/%Y')
    assert [r['amount'] for r in rows]==[-4,-4,20] and rows[1]['duplicate']

@pytest.mark.parametrize('text',[b'',b'a,a\n1,2',b'\xff',b'heading\n'])
def test_invalid_csv(text):
    with pytest.raises(ValueError): parse_csv(text)

@pytest.mark.parametrize('months',[0,3,6,12])
def test_ai_json_values_and_privacy(finance,months):
    app,conn,user,a,b,parent,child=finance
    app.set_setting('dropbox_access_token','DO-NOT-EXPORT')
    result=financial_review(conn,'monthly',TODAY,'GBP',1.2,'2.7.0',history=months,today=TODAY)
    encoded=json.dumps(result,allow_nan=False)
    assert all(secret not in encoded for secret in ['DO-NOT-EXPORT','secret-hash','password','receipt_path','created_by','user_id'])
    assert result['accounts'][0]['current_balance']==950
    assert result['period_expenditure']['total']==50
    assert result['period_expenditure']['by_category']['Test Household']==50
    assert result['targets']['target']==100 and result['targets']['projected']==110
    assert len(result['recurring'])==3
    assert result['forecast']['90']['projected']==1470
    assert result['historical_context']['trend'] is None
    assert len(result['historical_context']['periods'])==months

def test_history_trends(finance):
    _,conn,user,a,b,parent,child=finance
    for month,amount in [(6,-10),(7,-20),(8,-30)]:
        conn.execute('INSERT INTO transactions(account_id,tx_date,description,amount,category_id) VALUES(?,?,?,?,?)',(a,f'2026-{month:02d}-05','History',amount,child))
    r=financial_review(conn,'monthly',TODAY,'GBP',1.2,'2.7.0',history=3,today=TODAY)['historical_context']
    assert r['average_category_spend']['Test Household']==20
    assert r['trend']['expense']['absolute_change']==20
    assert r['trend']['expense']['percent_change']==200

@pytest.mark.parametrize('path',['/','/budgets/report','/recurring/','/planning/upcoming','/planning/upcoming?view=7','/planning/forecast?view=90','/planning/search','/planning/search?status=all','/planning/import','/planning/ai-review','/planning/ai-review?format=json','/planning/targets.csv','/planning/search?format=csv','/quick','/transfer','/settings','/system'])
def test_routes_start(appmod,path):
    appmod.set_setting('auth_required','0'); appmod.set_setting('tailnet_only','0')
    assert appmod.app.test_client().get(path).status_code==200


def test_import_http_review_required_and_replay(finance,source):
    app,conn,user,a,*_=finance
    app.set_setting('auth_required','0'); app.set_setting('tailnet_only','0')
    client=app.app.test_client()
    with client.session_transaction() as s: s['csrf']='test'
    csrf={'_csrf':'test'}
    response=client.post('/planning/import',data=dict(csrf,step='upload',file=(io.BytesIO(b'Date,Description,Amount\n2026-09-08,Imported,-15\n'),'test.csv')))
    assert response.status_code==200
    token=re.search(rb'name="token" value="([^"]+)"',response.data)[1].decode()
    assert client.post('/planning/import',data=dict(csrf,step='import',token=token)).status_code==400
    response=client.post('/planning/import',data=dict(csrf,step='review',token=token,map_date='Date',map_description='Description',map_amount='Amount',account_id=a))
    assert response.status_code==200 and b'Review before importing' in response.data
    response=client.post('/planning/import',data=dict(csrf,step='import',token=token,selected='1'))
    assert response.status_code==200 and b'Import complete' in response.data
    assert client.post('/planning/import',data=dict(csrf,step='import',token=token,selected='1')).status_code==400
    assert conn.execute("SELECT COUNT(*) FROM transactions WHERE description='Imported'").fetchone()[0]==1


def test_readonly_import_rejected(finance):
    app,conn,user,*_=finance
    app.set_setting('auth_required','1'); app.set_setting('tailnet_only','0')
    conn.execute("UPDATE users SET role='readonly' WHERE id=?",(user,)); conn.commit()
    client=app.app.test_client()
    with client.session_transaction() as s: s.update(user_id=user,auth_version=1,csrf='test')
    assert client.post('/planning/import',data={'_csrf':'test','step':'upload'}).status_code==403


def test_repeatable_migration_preserves_financial_rows(finance):
    _,conn,*_=finance
    tables=['accounts','transactions','categories','category_targets','recurring_rules']
    before={t:[tuple(r) for r in conn.execute('SELECT * FROM '+t)] for t in tables}
    migrate_v270(conn); migrate_v270(conn)
    assert before=={t:[tuple(r) for r in conn.execute('SELECT * FROM '+t)] for t in tables}
    assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'


def test_backup_and_dropbox_adapter(finance, tmp_path, monkeypatch):
    app, conn, *_ = finance
    app.set_setting('backup_location', str(tmp_path / 'backups'))
    ok, _, path = app.create_local_backup()
    assert ok
    with sqlite3.connect(path) as restored:
        assert restored.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert restored.execute('SELECT COUNT(*) FROM transactions').fetchone()[0] == 1
    calls = []
    def fake_request(endpoint, payload=None, content=None):
        calls.append((endpoint, payload, content))
        return {'name': {'display_name': 'Synthetic account'}}
    monkeypatch.setattr(app, 'dropbox_request', fake_request)
    assert app.test_dropbox_connection()[0]
    assert app.upload_backup_to_dropbox(path)[0]
    assert calls[-1][0] == 'files/upload'
    assert calls[-1][2].startswith(b'SQLite format 3')
    assert app.get_setting('dropbox_pending_path') == ''
    app.schedule_dropbox_retry(path, 'Synthetic failure')
    assert app.get_setting('dropbox_retry_count') == '1'
    assert app.get_setting('dropbox_pending_path') == path
    assert not app.dropbox_retry_due()
