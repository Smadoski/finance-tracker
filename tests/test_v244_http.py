def csrf(client):
    with client.session_transaction() as s: s['csrf']='testcsrf'
    return 'testcsrf'

def test_zero_transfer_rejected(appmod):
    appmod.set_setting('tailnet_only','0'); appmod.set_setting('auth_required','0')
    conn=appmod.db()
    conn.execute("INSERT INTO accounts(name,account_type,currency,opening_balance,active) VALUES('A','current','GBP',100,1)")
    conn.execute("INSERT INTO accounts(name,account_type,currency,opening_balance,active) VALUES('B','current','GBP',0,1)")
    a=conn.execute("SELECT id FROM accounts WHERE name='A'").fetchone()['id']; b=conn.execute("SELECT id FROM accounts WHERE name='B'").fetchone()['id']
    conn.commit(); conn.close()
    with appmod.app.test_client() as c:
        token=csrf(c)
        c.post('/transfer',data={'_csrf':token,'from_account':str(a),'to_account':str(b),'from_amount':'0','to_amount':'0','tx_date':'2026-08-27'})
    conn=appmod.db(); assert conn.execute("SELECT COUNT(*) n FROM transactions WHERE transfer_group IS NOT NULL").fetchone()['n']==0; conn.close()
