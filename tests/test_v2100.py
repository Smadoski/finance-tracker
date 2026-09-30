"""Release acceptance: debt ledger, upgrades, refunds, forecasts and Home."""
from datetime import date
import pytest
from finance_tracker.accounts import account_balance
from finance_tracker.health import financial_health
from finance_tracker.ai_review import period_totals, financial_review
from finance_tracker.budgets import category_actual
from finance_tracker.forecasting import forecast, estimated_forecast
from finance_tracker.recurring import validate_rule, process_rule_occurrence
from finance_tracker.csv_io import preview_import

@pytest.fixture
def ledger(appmod):
    appmod.set_setting('auth_required','0'); appmod.set_setting('tailnet_only','0'); appmod.set_setting('fx_auto','0')
    conn=appmod.db()
    bank=conn.execute("INSERT INTO accounts(name,account_type,currency,opening_balance,asset_class) VALUES('Favourite bank','current','EUR',1000,'accessible')").lastrowid
    card=conn.execute("INSERT INTO accounts(name,account_type,currency,opening_balance) VALUES('My card','credit_card','EUR',200)").lastrowid
    liability=conn.execute("INSERT INTO accounts(name,account_type,currency,opening_balance) VALUES('Old debt','liability','EUR',500)").lastrowid
    cat=conn.execute("INSERT INTO categories(name,kind) VALUES('Card shopping','expense')").lastrowid
    conn.commit(); client=appmod.app.test_client()
    with client.session_transaction() as s:s['csrf']='test'
    yield appmod,conn,client,bank,card,liability,cat
    conn.close()

def balance(conn,aid): return account_balance(conn,conn.execute('SELECT * FROM accounts WHERE id=?',(aid,)).fetchone())

def post(client,url,**values):
    return client.post(url,data=dict(_csrf='test',**values),follow_redirects=True)

def buy(client,card,cat,amount=100,refund=False):
    return post(client,'/transactions',account_id=card,category_id=cat,amount=amount,description='Purchase or refund',tx_date='2026-08-10',refund='1' if refund else '')

def test_purchase_refund_repayment_edit_delete_and_report(ledger):
    app,c,client,bank,card,debt,cat=ledger
    assert buy(client,card,cat).status_code==200
    buy(client,card,cat,25,True)
    assert balance(c,card)==275
    post(client,'/transfer',from_account=bank,to_account=card,from_amount=150,to_amount=150,tx_date='2026-08-11')
    assert balance(c,bank)==850 and balance(c,card)==125
    health=financial_health(c,'EUR',1.2,date(2026,9,27))
    assert health['actual']['net_worth']==225  # 850 - 125 - 500
    totals=period_totals(c,date(2026,8,1),date(2026,8,31),'EUR',1.2)
    assert totals['expense']['total']==75 and totals['income']['total']==0
    assert category_actual(c,cat,date(2026,8,1),date(2026,8,31),'EUR',1.2)==75
    refund=c.execute('SELECT id FROM transactions WHERE account_id=? AND amount=25',(card,)).fetchone()[0]
    post(client,f'/transaction/{refund}/category',category_id=cat)
    assert balance(c,card)==125
    post(client,f'/transaction/{refund}/edit',amount=30,category_id=cat,description='Refund',tx_date='2026-08-10',refund='1')
    assert balance(c,card)==120
    transfer=c.execute('SELECT id FROM transactions WHERE account_id=? AND transfer_group IS NOT NULL',(card,)).fetchone()[0]
    post(client,f'/transaction/{transfer}/delete')
    assert balance(c,bank)==1000 and balance(c,card)==270
    post(client,f'/transaction/{refund}/delete')
    assert balance(c,card)==300
    assert not c.execute('PRAGMA foreign_key_check').fetchall()


def test_credit_balance_increases_net_worth(ledger):
    _,c,client,bank,card,debt,cat=ledger
    buy(client,card,cat,250,True)
    assert balance(c,card)==-50
    health=financial_health(c,'EUR',1.2,date(2026,9,27))
    assert health['actual']['net_worth']==550
    assert health['actual']['liabilities']==450


def test_explicit_conversion_preserves_debt_and_history(ledger):
    _,c,client,bank,card,debt,cat=ledger
    c.execute("INSERT INTO valuations(account_id,valuation_date,value,notes) VALUES(?,'2026-09-01',425,'Existing valuation')",(debt,))
    c.execute("INSERT INTO transactions(account_id,tx_date,description,amount) VALUES(?,'2026-08-01','Historical ignored entry',-50)",(debt,));c.commit()
    values=dict(name='Old debt',account_type='credit_card',currency='EUR',opening_balance=999,active='1')
    response=post(client,f'/account/{debt}/edit',**values)
    assert b'Confirm conversion' in response.data and balance(c,debt)==425
    post(client,f'/account/{debt}/edit',confirm_card_conversion='1',**values)
    assert balance(c,debt)==425
    assert c.execute('SELECT opening_balance FROM accounts WHERE id=?',(debt,)).fetchone()[0]==375
    assert c.execute('SELECT COUNT(*) FROM valuations WHERE account_id=?',(debt,)).fetchone()[0]==1
    buy(client,debt,cat,20)
    assert balance(c,debt)==445
    assert b'Valuations retained' in client.get(f'/account/{debt}').data
    response=post(client,f'/account/{debt}/edit',name='Old debt',account_type='liability',currency='EUR',opening_balance=375,active='1')
    assert b'different debt model' in response.data and balance(c,debt)==445


def test_quick_refund_remains_pending_then_posts(ledger):
    _,c,client,bank,card,debt,cat=ledger
    post(client,'/quick',account_id=card,category_id=cat,amount=30,description='Card return',entry_type='expense',refund='1',tx_date='2026-08-15')
    pending=c.execute('SELECT * FROM pending_transactions').fetchone()
    assert pending['amount']==30 and balance(c,card)==200
    assert b'name="refund" value="1" checked' in client.get('/pending').data
    post(client,f'/pending/{pending["id"]}/post',amount=30,category_id=cat,entry_type='expense',refund='1',description='Card return',tx_date='2026-08-15')
    assert balance(c,card)==170


def rule(c,account,cat,kind='expense',to=None):
    values=validate_rule(c,dict(description='Scheduled card activity',transaction_type=kind,account_id=account,to_account_id=to,amount=50,category_id=cat if kind=='expense' else None,start_date='2026-10-01',frequency='monthly',working_day_adjustment='exact',posting_mode='automatic'))
    keys=list(values); rid=c.execute('INSERT INTO recurring_rules('+','.join(keys)+') VALUES('+','.join('?' for _ in keys)+')',list(values.values())).lastrowid;c.commit()
    return c.execute('SELECT * FROM recurring_rules WHERE id=?',(rid,)).fetchone()


def test_recurring_card_and_cash_forecasts_reconcile(ledger):
    _,c,client,bank,card,debt,cat=ledger
    expense=rule(c,card,cat); repayment=rule(c,bank,cat,'transfer',card)
    result=forecast(c,date(2026,10,1),date(2026,10,2),'EUR',1.2)
    assert result['current']==1000 and result['projected']==950 and result['expense']==0
    assert result['cards'][0]['current']==200 and result['cards'][0]['projected']==200
    process_rule_occurrence(c,expense,'2026-10-01');process_rule_occurrence(c,repayment,'2026-10-01');c.commit()
    assert balance(c,bank)==950 and balance(c,card)==200
    assert forecast(c,date(2026,10,1),date(2026,10,2),'EUR',1.2)['cards'][0]['transactions']==[]
    scoped=forecast(c,date(2026,10,1),date(2026,10,2),'EUR',1.2,[card])
    assert scoped['accounts']==[] and len(scoped['cards'])==1


def test_refunds_reduce_classified_estimates_and_card_forecast(ledger):
    _,c,client,bank,card,debt,cat=ledger
    buy(client,card,cat,100);buy(client,card,cat,20,True)
    c.execute("UPDATE transactions SET expense_type='normal',spending_class='essential' WHERE account_id=?",(card,));c.commit()
    h=financial_health(c,'EUR',1.2,date(2026,9,1))
    assert h['model']['normal_monthly_cost']==80 and h['operating']['monthly_income']==0
    result=estimated_forecast(c,date(2026,9,1),date(2026,9,30),'EUR',1.2,health=h)
    assert result['projected']==1000
    assert result['cards'][0]['projected']>280


def test_csv_cards_refunds_and_export_allowlist(ledger):
    _,c,client,bank,card,debt,cat=ledger
    source=dict(headers=['Date','Description','Amount','Category'],rows=[['2026-09-01','Refund','25','Card shopping']])
    rows=preview_import(c,source,dict(date='Date',description='Description',amount='Amount',category='Category'),card)
    assert rows[0]['error'] is None and rows[0]['amount']==25
    rule(c,card,cat)
    result=financial_review(c,'monthly',date(2026,10,1),'EUR',1.2,'2.10.0',today=date(2026,10,1))
    for projection in result['forecast'].values():
        for row in projection['cards']:
            assert 'account_id' not in row
            assert all('rule_id' not in t for t in row['transactions'])


@pytest.mark.parametrize('path',['/','/reports/overview','/accounts','/transactions','/quick','/pending','/planning/forecast','/health/estimated-forecast','/reports/recurring','/report/net-worth.pdf'])
def test_new_release_pages(ledger,path):
    _,c,client,*_=ledger
    assert client.get(path).status_code==200


def test_home_favourites_attention_and_retained_reports(ledger):
    app,c,client,bank,card,debt,cat=ledger
    app.set_setting('dashboard_account_1_id',str(bank));app.set_setting('dashboard_account_2_id',str(card))
    for i in range(8): buy(client,card,cat,i+1)
    html=client.get('/').data.decode()
    assert html.index('Favourite accounts')<html.index('Available cash')<html.index('Recent transactions')
    assert html.count('Purchase or refund')==5
    assert 'This month · Financial planning' not in html
    assert 'This month · Financial planning' in client.get('/reports/overview').data.decode()
    c.execute("UPDATE accounts SET active=0 WHERE id=?",(card,));c.commit()
    html=client.get('/').data.decode()
    assert 'href="/account/'+str(card)+'"' not in html


def test_valuation_and_archived_transfers_rejected(ledger):
    _,c,client,bank,card,debt,cat=ledger
    post(client,'/transfer',from_account=bank,to_account=debt,from_amount=50,to_amount=50)
    assert c.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]==0
    c.execute('UPDATE accounts SET active=0 WHERE id=?',(card,));c.commit()
    post(client,'/transfer',from_account=bank,to_account=card,from_amount=50,to_amount=50)
    assert c.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]==0


def test_cross_currency_repayment_and_readonly_protection(ledger):
    app,c,client,bank,card,debt,cat=ledger
    c.execute("UPDATE accounts SET currency='GBP' WHERE id=?",(card,));c.commit()
    post(client,'/transfer',from_account=bank,to_account=card,from_amount=120,to_amount=100,tx_date='2026-09-27')
    assert balance(c,bank)==880 and balance(c,card)==100
    assert financial_health(c,'EUR',1.2,date(2026,9,27))['actual']['net_worth']==260
    app.set_setting('auth_required','1')
    uid=c.execute("INSERT INTO users(name,username,password_hash,role) VALUES('Reader','reader','unused','readonly')").lastrowid;c.commit()
    with client.session_transaction() as s:s['user_id']=uid;s['auth_version']=1
    before='\n'.join(c.iterdump())
    response=client.post(f'/account/{debt}/edit',data=dict(_csrf='test',name='Debt',account_type='credit_card',currency='EUR',opening_balance=500,confirm_card_conversion='1'))
    assert response.status_code==403
    assert '\n'.join(c.iterdump())==before


def test_capital_refund_offsets_capital_ledger(ledger):
    _,c,client,bank,card,debt,cat=ledger
    buy(client,card,cat,100);buy(client,card,cat,20,True)
    c.execute("UPDATE transactions SET expense_type='capital' WHERE account_id=?",(card,))
    c.execute("INSERT INTO capital_movements(account_id,movement_date,amount,kind) VALUES(?,'2026-08-01',1000,'opening')",(bank,));c.commit()
    result=financial_health(c,'EUR',1.2,date(2026,9,1))
    assert result['capital']['capital_expenditure']==80
    assert result['capital']['closing']==920
