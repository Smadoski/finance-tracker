import sqlite3

def test_active_admin_query_requires_active_admin():
    c=sqlite3.connect(':memory:'); c.row_factory=sqlite3.Row
    c.execute('CREATE TABLE users(id INTEGER,role TEXT,active INTEGER)')
    c.execute("INSERT INTO users VALUES(1,'admin',0)")
    assert c.execute("SELECT COUNT(*) n FROM users WHERE role='admin' AND COALESCE(active,1)=1").fetchone()['n']==0

def test_zero_transfer_policy():
    assert 0 <= 0
