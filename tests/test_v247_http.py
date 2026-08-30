def csrf(client):
    with client.session_transaction() as session:
        session['csrf']='testcsrf'
    return 'testcsrf'


def no_auth(appmod):
    appmod.set_setting('tailnet_only','0')
    appmod.set_setting('auth_required','0')


def add_account(appmod,name='Test',account_type='current',currency='GBP'):
    conn=appmod.db()
    conn.execute(
        'INSERT INTO accounts(name,account_type,currency,opening_balance,active) VALUES(?,?,?,?,1)',
        (name,account_type,currency,100),
    )
    account_id=conn.execute('SELECT id FROM accounts WHERE name=?',(name,)).fetchone()['id']
    conn.commit(); conn.close()
    return account_id


def test_edit_account_rejects_invalid_currency_without_change(appmod):
    no_auth(appmod); account_id=add_account(appmod)
    with appmod.app.test_client() as client:
        token=csrf(client)
        response=client.post(f'/account/{account_id}/edit',data={
            '_csrf':token,'name':'Changed','account_type':'current','currency':'USD',
            'opening_balance':'200','institution':'','notes':'','active':'1',
        },follow_redirects=True)
        assert response.status_code==200
        assert b'Choose a valid currency' in response.data
    conn=appmod.db(); account=conn.execute('SELECT name,currency,opening_balance FROM accounts WHERE id=?',(account_id,)).fetchone(); conn.close()
    assert (account['name'],account['currency'],account['opening_balance'])==('Test','GBP',100)


def test_post_pending_rejects_malformed_amount_and_preserves_item(appmod):
    no_auth(appmod); account_id=add_account(appmod)
    conn=appmod.db()
    conn.execute("INSERT INTO pending_transactions(account_id,tx_date,description,amount,entry_type) VALUES(?,?,?,?,?)",(account_id,'2026-08-30','Pending',-10,'expense'))
    pending_id=conn.execute("SELECT id FROM pending_transactions WHERE description='Pending'").fetchone()['id']; conn.commit(); conn.close()
    with appmod.app.test_client() as client:
        token=csrf(client)
        response=client.post(f'/pending/{pending_id}/post',data={'_csrf':token,'amount':'not-money','category_id':'','entry_type':'expense'},follow_redirects=True)
        assert response.status_code==200
        assert b'Enter a valid amount and category' in response.data
    conn=appmod.db()
    assert conn.execute('SELECT COUNT(*) n FROM pending_transactions WHERE id=?',(pending_id,)).fetchone()['n']==1
    assert conn.execute("SELECT COUNT(*) n FROM transactions WHERE description='Pending'").fetchone()['n']==0
    conn.close()


def test_quick_entry_rejects_non_transaction_account(appmod):
    no_auth(appmod); account_id=add_account(appmod,account_type='other_asset')
    with appmod.app.test_client() as client:
        token=csrf(client)
        response=client.post('/quick',data={
            '_csrf':token,'action':'save','account_id':str(account_id),'tx_date':'2026-08-30',
            'description':'Invalid target','amount':'5','category_id':'','entry_type':'expense','notes':'',
        },follow_redirects=True)
        assert response.status_code==200
        assert b'Choose a valid account' in response.data
    conn=appmod.db(); assert conn.execute("SELECT COUNT(*) n FROM pending_transactions WHERE description='Invalid target'").fetchone()['n']==0; conn.close()


def test_pdf_share_mode_is_inline_and_download_mode_is_attachment(appmod):
    no_auth(appmod)
    with appmod.app.test_client() as client:
        inline=client.get('/report/net-worth.pdf?share=1')
        download=client.get('/report/net-worth.pdf')
    assert inline.status_code==200 and inline.mimetype=='application/pdf'
    assert inline.headers['Content-Disposition'].startswith('inline;')
    assert download.headers['Content-Disposition'].startswith('attachment;')


def test_dashboard_contains_ios_native_pdf_flow(appmod):
    no_auth(appmod)
    with appmod.app.test_client() as client:
        response=client.get('/')
    assert b'isIOSDevice' in response.data
    assert b"searchParams.set('share','1')" in response.data
