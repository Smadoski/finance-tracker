def csrf(client):
    with client.session_transaction() as session:
        session['csrf']='v251'
    return 'v251'


def no_auth(appmod):
    appmod.set_setting('tailnet_only','0')
    appmod.set_setting('auth_required','0')


def seed_account(appmod):
    conn=appmod.db()
    account=conn.execute("INSERT INTO accounts(name,account_type,currency) VALUES('Mobile Current','current','GBP')").lastrowid
    expense=conn.execute("SELECT id FROM categories WHERE kind='expense' ORDER BY id LIMIT 1").fetchone()['id']
    conn.commit(); conn.close()
    return account,expense


def test_target_forms_use_native_single_choice_selectors(appmod):
    no_auth(appmod); client=appmod.app.test_client()
    page=client.get('/budgets/')
    assert page.status_code==200
    for field in (b'name="category_id"',b'name="currency"',b'name="period"'):
        assert field in page.data
    assert b'value="weekly"' in page.data and b'value="yearly"' in page.data


def test_target_create_and_edit_category_period_currency(appmod):
    no_auth(appmod); account,category=seed_account(appmod)
    conn=appmod.db(); second=conn.execute("INSERT INTO categories(name,kind) VALUES('Mobile Budget','expense')").lastrowid; conn.commit(); conn.close()
    client=appmod.app.test_client(); token=csrf(client)
    response=client.post('/budgets/',data={'_csrf':token,'category_id':category,'target_amount':'100','currency':'GBP','period':'weekly','active':'1'})
    assert response.status_code==200
    conn=appmod.db(); target=conn.execute('SELECT * FROM category_targets WHERE category_id=?',(category,)).fetchone(); conn.close()
    edit=client.get(f'/budgets/{target["id"]}/edit')
    assert edit.status_code==200 and b'name="category_id"' in edit.data
    response=client.post(f'/budgets/{target["id"]}/edit',data={'_csrf':token,'category_id':second,'target_amount':'125','currency':'EUR','period':'yearly','active':'1'})
    assert response.status_code in (301,302)
    conn=appmod.db(); changed=conn.execute('SELECT * FROM category_targets WHERE id=?',(target['id'],)).fetchone(); conn.close()
    assert (changed['category_id'],changed['period'],changed['currency'],changed['target_amount'])==(second,'yearly','EUR',125)


def test_recurring_form_selectors_and_existing_rule_edit(appmod):
    no_auth(appmod); account,category=seed_account(appmod)
    client=appmod.app.test_client(); token=csrf(client)
    page=client.get('/recurring/')
    for field in (b'transaction_type',b'account_id',b'category_id',b'frequency',b'posting_mode',b'working_day_adjustment'):
        assert b'name="'+field+b'"' in page.data
    response=client.post('/recurring/',data={'_csrf':token,'description':'Mobile rent','transaction_type':'expense','account_id':account,'amount':'10','category_id':category,'start_date':'2026-09-01','frequency':'quarterly','working_day_adjustment':'next','posting_mode':'pending','active':'1'})
    assert response.status_code==200
    conn=appmod.db(); rule=conn.execute("SELECT * FROM recurring_rules WHERE description='Mobile rent'").fetchone(); conn.close()
    edit=client.get(f'/recurring/{rule["id"]}/edit')
    assert edit.status_code==200 and b'value="quarterly" selected' in edit.data and b'value="next" selected' in edit.data and b'value="pending" selected' in edit.data


def test_multi_account_report_selection_is_preserved(appmod):
    no_auth(appmod); seed_account(appmod)
    conn=appmod.db(); conn.execute("INSERT INTO accounts(name,account_type,currency) VALUES('Second Mobile','current','EUR')"); conn.commit(); conn.close()
    data=appmod.app.test_client().get('/budgets/report').data
    assert data.count(b'type="checkbox" name="account_id"')==2


def test_mobile_styles_and_status_settings_contract(appmod):
    no_auth(appmod); client=appmod.app.test_client()
    css=client.get('/static/style.css').data
    assert b'@media(max-width:430px)' in css and b'.responsive-table thead' in css and b'min-height:46px' in css
    appmod.set_setting('licensed_to','Mobile Licence'); appmod.set_setting('licence_number','FT-251')
    # Information architecture remains unchanged; routes are admin pages when authentication is enabled.
    assert b'Mobile Licence' in client.get('/system').data
    assert b'Licence Configuration' in client.get('/settings').data
