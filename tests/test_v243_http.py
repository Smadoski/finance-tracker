def set_csrf(client):
    with client.session_transaction() as s: s['csrf']='testcsrf'
    return 'testcsrf'

def test_readonly_cannot_write(appmod):
    appmod.set_setting('tailnet_only','0'); appmod.set_setting('auth_required','1')
    from werkzeug.security import generate_password_hash
    conn=appmod.db()
    conn.execute("INSERT INTO users(name,username,password_hash,role,active,auth_version) VALUES(?,?,?,?,1,1)",('Reader','reader',generate_password_hash('longpassword'),'readonly'))
    uid=conn.execute("SELECT id FROM users WHERE username='reader'").fetchone()['id']; conn.commit(); conn.close()
    with appmod.app.test_client() as c:
        with c.session_transaction() as s: s['user_id']=uid; s['auth_version']=1; s['csrf']='testcsrf'
        assert c.post('/transactions',data={'_csrf':'testcsrf'}).status_code==403

def test_uncategorised_edit_preserves_negative(appmod):
    appmod.set_setting('tailnet_only','0'); appmod.set_setting('auth_required','0')
    conn=appmod.db()
    conn.execute("INSERT INTO accounts(name,account_type,currency,opening_balance,active) VALUES('A','current','GBP',0,1)")
    aid=conn.execute("SELECT id FROM accounts WHERE name='A'").fetchone()['id']
    conn.execute("INSERT INTO transactions(account_id,tx_date,description,amount) VALUES(?,?,?,?)",(aid,'2026-08-27','Test',-10))
    tid=conn.execute("SELECT id FROM transactions WHERE description='Test'").fetchone()['id']; conn.commit(); conn.close()
    with appmod.app.test_client() as c:
        token=set_csrf(c)
        r=c.post(f'/transaction/{tid}/edit',data={'_csrf':token,'tx_date':'2026-08-27','description':'Test','amount':'12','category_id':'','tags':'','notes':''})
        assert r.status_code in (301,302)
    conn=appmod.db(); assert conn.execute('SELECT amount FROM transactions WHERE id=?',(tid,)).fetchone()['amount']==-12; conn.close()
