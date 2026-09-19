import json
import sqlite3
from datetime import date
import pytest
from finance_tracker.health import financial_health, scenario, converted
from finance_tracker.migrations import migrate_v290
from finance_tracker.classifications import save_classification
from finance_tracker.recurring import process_rule_occurrence, resolve_pending_occurrence, process_due
from finance_tracker.upcoming import upcoming
from finance_tracker.ai_review import financial_review

TODAY=date(2026,9,19)

@pytest.fixture
def healthdb(appmod):
    conn=appmod.db()
    ids=[]
    for name,kind,currency,balance,asset in [('Everyday','current','EUR',10000,'designated'),('Savings','savings','GBP',10000,'accessible'),('Pension','pension','GBP',30000,'retirement'),('Vehicle','other_asset','EUR',5000,'other'),('Debt','liability','EUR',1000,'unclassified')]:
        ids.append(conn.execute('INSERT INTO accounts(name,account_type,currency,opening_balance,asset_class) VALUES(?,?,?,?,?)',(name,kind,currency,balance,asset)).lastrowid)
    cat=conn.execute("INSERT INTO categories(name,kind) VALUES('Housing test','expense')").lastrowid
    food=conn.execute("INSERT INTO categories(name,kind) VALUES('Food test','expense')").lastrowid
    src=conn.execute("SELECT id FROM funding_sources WHERE name='Designated capital'").fetchone()[0]
    for month in ('06','07','08'):
        for description,amount,expense,income,category in [('Rent',-1000,'normal','unclassified',cat),('Food',-200,'normal','unclassified',food),('Salary',1800,'unclassified','salary',None),('Interest',100,'unclassified','investment',None)]:
            conn.execute('INSERT INTO transactions(account_id,tx_date,description,amount,expense_type,income_type,category_id,spending_class,funding_source_id) VALUES(?,?,?,?,?,?,?,?,?)',(ids[0],f'2026-{month}-15',description,amount,expense,income,category,'essential',src))
    conn.execute("INSERT INTO transactions(account_id,tx_date,description,amount,expense_type) VALUES(?,'2026-08-20','Capital appliance',-3000,'capital')",(ids[0],))
    conn.execute("INSERT INTO transactions(account_id,tx_date,description,amount,income_type) VALUES(?,'2026-08-21','Prize',30000,'extraordinary')",(ids[0],))
    rule=conn.execute("INSERT INTO recurring_rules(description,transaction_type,account_id,amount,category_id,start_date,next_scheduled_date,frequency,expense_type,funding_source_id) VALUES('Rent','expense',?,1000,?,'2026-06-01','2026-09-20','monthly','normal',?)",(ids[0],cat,src)).lastrowid
    conn.commit()
    yield appmod,conn,ids,cat,food,rule
    conn.close()


def test_operating_separates_capital_and_prize_keeps_capital_funded_rent(healthdb):
    _,conn,ids,*_=healthdb
    health=financial_health(conn,'EUR',1.2,TODAY)
    assert health['model']['normal_monthly_cost']==1200
    assert health['operating']['monthly_income']==1900
    assert health['operating']['monthly_surplus']==700
    assert health['operating']['annual_surplus']==8400
    assert health['operating']['income_coverage']==pytest.approx(1900/1200*100)
    assert health['excluded_expenses_observed']['capital']==3000
    assert health['history']['maturity']=='preliminary'
    assert health['history']['months']==3
    assert health['estimated_additional_monthly_by_account'][str(ids[0])]==200


def test_stress_preserves_every_database_row(healthdb):
    _,conn,*_=healthdb; before='\n'.join(conn.iterdump())
    health=financial_health(conn,'EUR',1.2,TODAY)
    selected=[s['key'] for s in health['model']['income_sources'] if s['type']!='investment']
    result=scenario(health['model'],selected)
    assert result['monthly_income']==1800
    assert result['monthly_surplus']==600
    assert result['extraordinary_monthly_observed']==10000
    assert scenario(health['model'],[])['monthly_capital_requirement']==1200
    assert '\n'.join(conn.iterdump())==before


def test_net_worth_currency_and_liability_reconcile(healthdb):
    _,conn,*_=healthdb; h=financial_health(conn,'EUR',1.2,TODAY)
    assert h['actual']['net_worth']==pytest.approx(sum(a['equivalent_balance'] for a in h['accounts']))
    assert h['actual']['other']==5000 and h['actual']['liabilities']==1000
    e=h['currency_exposure']; assert sum(a['percent'] for a in e['assets'])==pytest.approx(100)
    assert e['gbp_stronger_5']-e['eur_equivalent']==pytest.approx(40000*1.2*.05)
    assert e['eur_equivalent']-e['gbp_weaker_5']==pytest.approx(2400)
    assert converted(20,'CAD','CAD',1.2)==20
    assert converted(100,'CAD','EUR',{'CAD':0.65,'EUR':1})==65
    assert converted(100,'CAD','USD',{'CAD':0.65,'USD':0.8})==81.25
    with pytest.raises(ValueError,match='No configured'): converted(20,'CAD','EUR',1.2)


def add_strategy(conn,ids,end=None):
    sid=conn.execute("INSERT INTO funding_strategies(purpose,kind,currency,monthly_amount,start_date,end_date) VALUES('Temporary housing','housing','EUR',1200,'2026-09-19',?)",(end,)).lastrowid
    for index,(account,allocation) in enumerate(zip(ids[:3],[1200,2000,3000])):
        conn.execute('INSERT INTO funding_steps(strategy_id,position,account_id,allocation) VALUES(?,?,?,?)',(sid,index,account,allocation))
    conn.commit();return sid


def test_sequential_funding_transition_fx_and_end_date(healthdb):
    _,conn,ids,_,_,rule=healthdb; sid=add_strategy(conn,ids)
    h=financial_health(conn,'EUR',1.2,TODAY);f=h['housing'][0]
    assert f['current_source']['account']=='Everyday'
    assert f['next_source']['account']=='Savings'
    assert [s['runway_months'] for s in f['sources']]==[1,2,3]
    assert f['combined_runway_months']==6
    assert f['current_source']['transition_date']=='2026-10-19'
    assert f['sources'][2]['estimated_monthly_gross']==1000
    conn.execute("UPDATE funding_strategies SET end_date='2026-10-18' WHERE id=?",(sid,))
    conn.execute('UPDATE recurring_rules SET funding_strategy_id=? WHERE id=?',(sid,rule))
    conn.commit()
    capped=financial_health(conn,'EUR',1.2,TODAY)['housing'][0]
    assert capped['combined_runway_months']==pytest.approx(30/(365.25/12))
    assert capped['next_source'] is None
    assert all(r['scheduled_date']<='2026-10-18' for r in upcoming(conn,TODAY,date(2026,12,31)))
    process_due(conn,date(2026,12,31))
    assert conn.execute('SELECT COUNT(*) FROM transactions WHERE description=\'Rent\' AND tx_date>\'2026-10-18\'').fetchone()[0]==0


def test_pension_withdrawal_monitoring(healthdb):
    _,conn,ids,*_=healthdb; sid=add_strategy(conn,ids)
    conn.execute('UPDATE funding_steps SET allocation=0 WHERE position<2')
    conn.execute('UPDATE funding_steps SET monthly_gross=1200,monthly_net=900 WHERE position=2')
    conn.execute("INSERT INTO pension_withdrawals(account_id,withdrawal_date,gross,net) VALUES(?,'2026-09-01',1200,900)",(ids[2],))
    result=financial_health(conn,'EUR',1.2,TODAY)['housing'][0]['current_source']
    assert result['account']=='Pension'
    assert result['annual_gross']==14400
    assert result['withdrawal_percent']==48
    assert result['cumulative_gross_withdrawals']==1200
    assert result['net_shortfall']==100


def test_capital_ledger_reconciles(healthdb):
    _,conn,ids,*_=healthdb
    conn.execute("INSERT INTO capital_movements(account_id,movement_date,amount,kind) VALUES(?,'2026-06-01',5000,'opening')",(ids[0],))
    conn.execute("INSERT INTO capital_movements(account_id,movement_date,amount,kind) VALUES(?,'2026-07-01',-1000,'movement')",(ids[0],))
    ledger=financial_health(conn,'EUR',1.2,TODAY)['capital']
    assert ledger['opening']==5000 and ledger['extraordinary_income']==30000 and ledger['capital_expenditure']==3000
    assert ledger['closing']==31000


def test_classification_inheritance_and_pending_review(healthdb):
    _,conn,_,_,_,rule_id=healthdb
    conn.execute("UPDATE recurring_rules SET posting_mode='pending',spending_class='essential' WHERE id=?",(rule_id,))
    rule=conn.execute('SELECT * FROM recurring_rules WHERE id=?',(rule_id,)).fetchone()
    occurrence=process_rule_occurrence(conn,rule,'2026-09-20')
    pending=conn.execute('SELECT * FROM pending_transactions WHERE id=?',(occurrence['pending_id'],)).fetchone()
    assert pending['expense_type']=='normal' and pending['funding_source_id']==rule['funding_source_id']
    tx=conn.execute("INSERT INTO transactions(account_id,tx_date,description,amount) VALUES(?,'2026-09-20','Reviewed rent',-1000)",(rule['account_id'],)).lastrowid
    resolve_pending_occurrence(conn,pending['id'],tx)
    assert conn.execute('SELECT expense_type FROM transactions WHERE id=?',(tx,)).fetchone()[0]=='normal'
    assert conn.execute('SELECT spending_class FROM transactions WHERE id=?',(tx,)).fetchone()[0]=='essential'


def test_repeat_migration_preserves_values_settings_and_renamed_source(healthdb):
    _,conn,*_=healthdb
    conn.execute("UPDATE funding_sources SET name='Custom income' WHERE name='Current income'");conn.commit()
    before={t:[tuple(r) for r in conn.execute('SELECT * FROM '+t)] for t in ['accounts','transactions','categories','users','recurring_rules','settings','funding_sources']}
    migrate_v290(conn);migrate_v290(conn)
    for table,rows in before.items(): assert rows==[tuple(r) for r in conn.execute('SELECT * FROM '+table)]
    assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert not conn.execute('PRAGMA foreign_key_check').fetchall()


def test_export_schema_classifications_and_account_scope(healthdb):
    _,conn,ids,*_=healthdb;add_strategy(conn,ids)
    result=financial_review(conn,'quarterly',TODAY,'EUR',1.2,'2.9.0',today=TODAY)
    assert result['schema_version']=='finance-tracker.financial-review/2.9'
    assert 'forecast' in result and 'financial_health' in result
    rent=next(r for r in result['classified_transactions'] if r['description']=='Rent')
    assert rent['expense_type']=='normal' and rent['funding_source']=='Designated capital'
    assert result['financial_health']['housing']
    scoped=financial_review(conn,'monthly',TODAY,'EUR',1.2,'2.9.0',[ids[0]],today=TODAY)
    assert scoped['financial_health']['housing']==[]
    assert all(a['name']=='Everyday' for a in scoped['financial_health']['accounts'])
    assert 'password_hash' not in json.dumps(result)


@pytest.mark.parametrize('months,expected',[(0,'limited history'),(2,'limited history'),(3,'preliminary'),(6,'established'),(12,'mature annual view')])
def test_maturity(appmod,months,expected):
    from finance_tracker.recurring import month_shift
    conn=appmod.db();aid=conn.execute("INSERT INTO accounts(name,account_type,currency) VALUES('Empty','current','EUR')").lastrowid
    for n in range(1,months+1):
        conn.execute("INSERT INTO transactions(account_id,tx_date,description,amount,expense_type) VALUES(?,?,'Normal',-100,'normal')",(aid,str(month_shift(TODAY.replace(day=1),-n,1))))
    assert financial_health(conn,'EUR',1.2,TODAY)['history']['maturity']==expected
    conn.close()


def client_for(appmod,role='admin'):
    conn=appmod.db();uid=conn.execute("INSERT INTO users(name,username,password_hash,role) VALUES('Health user',?,'fake',?)",(role,role)).lastrowid;conn.commit();conn.close()
    appmod.set_setting('auth_required','1');appmod.set_setting('tailnet_only','0');appmod.set_setting('fx_auto','0');appmod.set_setting('backup_enabled','0')
    client=appmod.app.test_client()
    with client.session_transaction() as session: session['user_id']=uid;session['csrf']='test'
    return client


@pytest.mark.parametrize('path',['/health/','/health/classify','/health/classify?table=accounts','/health/classify?table=recurring_rules','/health/funding','/health/estimated-forecast','/planning/ai-review'])
def test_health_pages(healthdb,path):
    appmod,conn,ids,*_=healthdb;add_strategy(conn,ids)
    response=client_for(appmod).get(path)
    assert response.status_code==200,response.data[:500]


def test_health_writes_require_csrf_and_editor_permission(healthdb):
    appmod,conn,ids,*_=healthdb;client=client_for(appmod,'readonly')
    body=dict(_csrf='test',table='accounts',selected=str(ids[0]),asset_class='other')
    assert client.post('/health/classify',data=body).status_code==403
    assert conn.execute('SELECT asset_class FROM accounts WHERE id=?',(ids[0],)).fetchone()[0]=='designated'
    client=client_for(appmod,'admin');body.pop('_csrf')
    assert client.post('/health/classify',data=body).status_code==400


def test_classify_and_funding_validation_are_atomic(healthdb):
    appmod,conn,ids,*_=healthdb;client=client_for(appmod)
    response=client.post('/health/classify',data=dict(_csrf='test',table='accounts',selected=str(ids[0]),asset_class='accessible'))
    assert response.status_code==302
    assert conn.execute('SELECT asset_class FROM accounts WHERE id=?',(ids[0],)).fetchone()[0]=='accessible'
    count=conn.execute('SELECT COUNT(*) FROM funding_strategies').fetchone()[0]
    response=client.post('/health/funding',data=dict(_csrf='test',purpose='Invalid duplicate',monthly_amount='100',currency='EUR',account_id=[str(ids[0]),str(ids[0])],allocation=['',''],active='1'))
    assert response.status_code==400
    assert conn.execute('SELECT COUNT(*) FROM funding_strategies').fetchone()[0]==count


def test_ended_rent_not_projected_forever(healthdb):
    _,conn,ids,_,_,rule=healthdb
    conn.execute("UPDATE recurring_rules SET end_date='2026-08-31' WHERE id=?",(rule,))
    assert financial_health(conn,'EUR',1.2,TODAY)['model']['normal_monthly_cost']==200


def test_estimated_forecast_only_adds_normal_residual(healthdb):
    from finance_tracker.forecasting import forecast, estimated_forecast
    _,conn,ids,*_=healthdb;end=date(2026,10,18)
    baseline=forecast(conn,TODAY,end,'EUR',1.2)
    estimated=estimated_forecast(conn,TODAY,end,'EUR',1.2)
    extra=200*30/(365.25/12)
    assert estimated['estimated_additional']==pytest.approx(extra)
    assert estimated['projected']==pytest.approx(baseline['projected']-extra)
    assert estimated['expense']==baseline['expense']


def test_new_records_are_never_guessed_from_size_or_category(healthdb):
    _,conn,ids,cat,*_=healthdb
    tid=conn.execute("INSERT INTO transactions(account_id,tx_date,description,amount,category_id) VALUES(?,'2026-08-31','Huge purchase',-1000000,?)",(ids[0],cat)).lastrowid
    row=conn.execute('SELECT * FROM transactions WHERE id=?',(tid,)).fetchone()
    assert row['expense_type']=='unclassified' and row['income_type']=='unclassified'
    result=financial_health(conn,'EUR',1.2,TODAY)
    assert result['model']['normal_monthly_cost']==1200
    assert result['history']['unclassified_records']==1
    assert not result['retirement']['ready']


def test_migration_rolls_back_when_validation_fails(healthdb):
    _,conn,*_=healthdb
    conn.execute("UPDATE settings SET value='2.8.0' WHERE key='schema_version'")
    conn.execute("CREATE TRIGGER block_migration BEFORE INSERT ON settings WHEN NEW.key='schema_version' BEGIN SELECT RAISE(ABORT,'migration blocked'); END")
    conn.commit();before='\n'.join(conn.iterdump())
    with pytest.raises(sqlite3.IntegrityError): migrate_v290(conn)
    assert '\n'.join(conn.iterdump())==before


def test_funding_configuration_create_edit_and_monitoring(healthdb):
    appmod,conn,ids,*_=healthdb;client=client_for(appmod)
    data=dict(_csrf='test',purpose='Rent fund',kind='housing',monthly_amount='1200',currency='EUR',active='1',account_id=[str(i) for i in ids[:3]],allocation=['1200','2000','3000'],monthly_gross=['','','1100'],monthly_net=['','','1000'])
    assert client.post('/health/funding',data=data).status_code==302
    sid=conn.execute("SELECT id FROM funding_strategies WHERE purpose='Rent fund'").fetchone()[0]
    data.update(id=str(sid),monthly_amount='1500',end_date='2027-01-01')
    assert client.post('/health/funding',data=data).status_code==302
    assert conn.execute('SELECT COUNT(*) FROM funding_steps WHERE strategy_id=?',(sid,)).fetchone()[0]==3
    for body in [dict(action='capital',kind='opening',account_id=str(ids[0]),date='2026-06-01',amount='10000'),dict(action='capital',kind='movement',account_id=str(ids[0]),date='2026-07-01',amount='-1000'),dict(action='withdrawal',account_id=str(ids[2]),date='2026-07-01',amount='1000',net='850')]:
        assert client.post('/health/funding',data=dict(body,_csrf='test')).status_code==302
    assert conn.execute('SELECT COUNT(*) FROM pension_withdrawals').fetchone()[0]==1
    assert conn.execute('SELECT COUNT(*) FROM capital_movements').fetchone()[0]==2
    data['monthly_amount']='nan'
    assert client.post('/health/funding',data=data).status_code==400
    assert conn.execute('SELECT monthly_amount FROM funding_strategies WHERE id=?',(sid,)).fetchone()[0]==1500


def test_sequence_skips_empty_secondary_source(healthdb):
    _,conn,ids,*_=healthdb;add_strategy(conn,ids)
    conn.execute('UPDATE funding_steps SET allocation=0 WHERE position=1')
    result=financial_health(conn,'EUR',1.2,TODAY)['housing'][0]
    assert result['next_source']['account']=='Pension'
    assert result['combined_runway_months']==4
