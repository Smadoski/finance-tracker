import sqlite3

from finance_tracker.migrations import migrate_v250


def test_v247_database_migrates_repeatably_and_preserves_licence(tmp_path):
    path=tmp_path/'v247-copy.db'
    conn=sqlite3.connect(path); conn.row_factory=sqlite3.Row
    conn.executescript("""
        CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE users(id INTEGER PRIMARY KEY,name TEXT,username TEXT,password_hash TEXT,role TEXT);
        CREATE TABLE accounts(id INTEGER PRIMARY KEY,name TEXT,account_type TEXT,currency TEXT,active INTEGER);
        CREATE TABLE categories(id INTEGER PRIMARY KEY,name TEXT,kind TEXT,parent_id INTEGER);
        CREATE TABLE transactions(id INTEGER PRIMARY KEY,account_id INTEGER,tx_date TEXT,description TEXT,amount REAL,category_id INTEGER,tag_text TEXT,notes TEXT,transfer_group TEXT,created_by INTEGER);
        CREATE TABLE pending_transactions(id INTEGER PRIMARY KEY,account_id INTEGER,tx_date TEXT,description TEXT,amount REAL,category_id INTEGER,created_by INTEGER);
        INSERT INTO settings VALUES('licensed_to','Steph');
        INSERT INTO settings VALUES('licence_number','FT-247-KEEP');
        INSERT INTO accounts VALUES(1,'Current','bank','GBP',1);
        INSERT INTO transactions VALUES(1,1,'2024-01-01','Existing',-12.5,NULL,NULL,NULL,NULL,NULL);
    """)
    migrate_v250(conn); migrate_v250(conn)
    assert conn.execute("SELECT value FROM settings WHERE key='licensed_to'").fetchone()['value']=='Steph'
    assert conn.execute("SELECT value FROM settings WHERE key='licence_number'").fetchone()['value']=='FT-247-KEEP'
    assert conn.execute('SELECT amount FROM transactions WHERE id=1').fetchone()['amount']==-12.5
    for table in ('recurring_rules','recurring_occurrences','category_targets'):
        assert conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone()
    conn.close()


def login_as(client,appmod,role):
    appmod.set_setting('auth_required','1')
    conn=appmod.db()
    user_id=conn.execute("INSERT INTO users(name,username,password_hash,role) VALUES(?,?,?,?)",('Test',role,'x',role)).lastrowid
    conn.commit(); conn.close()
    with client.session_transaction() as session:
        session['user_id']=user_id
        session['auth_version']=1
        session['csrf']='test-csrf'


def test_status_contains_information_settings_remains_configurable(appmod):
    appmod.set_setting('licensed_to','Steph'); appmod.set_setting('licence_number','FT-KEEP')
    client=appmod.app.test_client(); login_as(client,appmod,'admin')
    status=client.get('/system'); settings=client.get('/settings')
    assert status.status_code==200 and b'Status' in status.data and b'FT-KEEP' in status.data and appmod.APP_VERSION.encode() in status.data
    assert settings.status_code==200 and b'Licence Configuration' in settings.data
    assert b'Information</h2>' not in settings.data


def test_readonly_cannot_modify_recurring_rules_or_targets(appmod):
    client=appmod.app.test_client(); login_as(client,appmod,'readonly')
    recurring=client.post('/recurring/',data={'_csrf':'test-csrf'})
    target=client.post('/budgets/',data={'_csrf':'test-csrf'})
    assert recurring.status_code==403 and target.status_code==403


def test_recurring_and_target_pages_start(appmod):
    client=appmod.app.test_client(); login_as(client,appmod,'admin')
    assert client.get('/recurring/').status_code==200
    assert client.get('/budgets/').status_code==200
    assert client.get('/budgets/report').status_code==200
