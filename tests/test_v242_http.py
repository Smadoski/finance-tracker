def csrf(c):
    with c.session_transaction() as s:s['csrf']='testcsrf'
    return 'testcsrf'
def test_no_auth_dashboard(appmod):
    appmod.set_setting('tailnet_only','0'); appmod.set_setting('auth_required','0')
    with appmod.app.test_client() as c:assert c.get('/').status_code==200
def test_quick_uncategorised_expense_negative(appmod):
    appmod.set_setting('tailnet_only','0'); appmod.set_setting('auth_required','0'); conn=appmod.db(); conn.execute("INSERT INTO accounts(name,account_type,currency,opening_balance,active) VALUES('Test','current','GBP',100,1)"); aid=conn.execute("SELECT id FROM accounts WHERE name='Test'").fetchone()['id']; conn.commit(); conn.close()
    with appmod.app.test_client() as c: token=csrf(c); r=c.post('/quick',data={'_csrf':token,'action':'save','account_id':str(aid),'tx_date':'2026-08-27','description':'Coffee','amount':'5.00','category_id':'','entry_type':'expense','notes':''}); assert r.status_code in (301,302)
    conn=appmod.db(); p=conn.execute("SELECT amount,entry_type FROM pending_transactions WHERE description='Coffee'").fetchone(); assert p['amount']==-5.0 and p['entry_type']=='expense'; conn.close()
