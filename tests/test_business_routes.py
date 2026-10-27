import hashlib
import sqlite3
from flask import Flask
from finance_tracker.business_export import export_transactions
from finance_tracker.business_routes import create_blueprint

SCHEMA = """
CREATE TABLE settings(key TEXT,value TEXT);
INSERT INTO settings VALUES('setup_complete','1'),('tailnet_only','1');
CREATE TABLE users(id INTEGER,active INTEGER,auth_version INTEGER,role TEXT);
INSERT INTO users VALUES(1,1,3,'readonly');
CREATE TABLE accounts(id INTEGER,name TEXT,institution TEXT,account_type TEXT,currency TEXT,opening_balance REAL,active INTEGER);
INSERT INTO accounts VALUES (1,'First Direct Current','First Direct','current','GBP',0,1),(2,'Wise Current Account EUR','Wise','current','EUR',0,1),(3,'Bank of Cyprus','BoC','current','EUR',0,1);
CREATE TABLE categories(id INTEGER,name TEXT,kind TEXT);
INSERT INTO categories VALUES (1,'Salary','income'),(2,'Transfer','transfer');
CREATE TABLE transactions(id INTEGER PRIMARY KEY,account_id INTEGER,tx_date TEXT,description TEXT,amount REAL,category_id INTEGER,tag_text TEXT,notes TEXT,transfer_group TEXT,receipt_path TEXT,created_by INTEGER,created_at TEXT);
INSERT INTO transactions VALUES (1,1,'2026-11-20','Horts invoice payment',1658.28,1,'','',NULL,NULL,1,'2026-11-21');
INSERT INTO transactions VALUES (2,1,'2026-11-21','Transfer to Wise',-500.00,2,'','','abc123',NULL,1,'2026-11-21');
INSERT INTO transactions VALUES (3,2,'2026-11-21','Transfer from First Direct',576.50,2,'','','abc123',NULL,1,'2026-11-21');
INSERT INTO transactions VALUES (4,3,'2026-11-25','Rent',-800.00,NULL,'','',NULL,NULL,1,'2026-11-25');
"""


def build(tmp_path):
    path = tmp_path / 'finance.db'
    with sqlite3.connect(path) as c:
        c.executescript(SCHEMA)
    app = Flask(__name__)
    app.register_blueprint(create_blueprint(lambda: path))
    return path, app.test_client()


def test_contract_is_readonly_scoped_and_revocable(tmp_path, monkeypatch):
    path, client = build(tmp_path)
    url = '/api/business/v1/transactions'
    secret = 'business-transactions-test-secret-32-chars!'
    monkeypatch.setenv('FINANCE_BUSINESS_TOKEN', secret)
    monkeypatch.setenv('FINANCE_BUSINESS_USER_ID', '1')
    monkeypatch.setenv('FINANCE_BUSINESS_USER_VERSION', '3')
    headers = {'Authorization': 'Bearer ' + secret}
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert client.get(url).status_code == 401
    response = client.get(url, headers=headers)
    assert response.status_code == 200
    assert response.json['contract'] == 'business-transactions-v1'
    assert len(response.json['transactions']) == 4
    first = response.json['transactions'][0]
    assert first['id'] == 4 and first['tx_date'] == '2026-11-25' and first['amount'] == '-800.00'
    assert response.headers['Cache-Control'] == 'no-store'
    assert client.post(url, headers=headers).status_code == 405
    assert client.get(url, headers=headers, environ_overrides={'REMOTE_ADDR': '203.0.113.1'}).status_code == 403
    monkeypatch.setenv('FINANCE_BUSINESS_USER_VERSION', '2')
    assert client.get(url, headers=headers).status_code == 403
    monkeypatch.setenv('FINANCE_BUSINESS_USER_VERSION', '3')
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest


def test_filters_transfer_groups_and_validation(tmp_path, monkeypatch):
    path, client = build(tmp_path)
    secret = 'business-transactions-test-secret-32-chars!'
    monkeypatch.setenv('FINANCE_BUSINESS_TOKEN', secret)
    monkeypatch.setenv('FINANCE_BUSINESS_USER_ID', '1')
    monkeypatch.setenv('FINANCE_BUSINESS_USER_VERSION', '3')
    headers = {'Authorization': 'Bearer ' + secret}
    gbp = client.get('/api/business/v1/transactions?account_id=1', headers=headers).json['transactions']
    assert [row['id'] for row in gbp] == [2, 1]
    assert all(row['currency'] == 'GBP' for row in gbp)
    transfer = client.get('/api/business/v1/transactions?q=transfer', headers=headers).json['transactions']
    assert [row['id'] for row in transfer] == [3, 2]
    assert all(row['transfer_group'] == 'abc123' for row in transfer)
    eur_leg = client.get('/api/business/v1/transactions?account_id=2', headers=headers).json['transactions']
    assert [row['id'] for row in eur_leg] == [3] and eur_leg[0]['currency'] == 'EUR'
    window = client.get('/api/business/v1/transactions?start=2026-11-20&end=2026-11-20&min_amount=1000', headers=headers).json['transactions']
    assert [row['id'] for row in window] == [1]
    assert client.get('/api/business/v1/transactions?start=bad', headers=headers).status_code == 400
    assert client.get('/api/business/v1/transactions?limit=0', headers=headers).status_code == 400
    assert client.get('/api/business/v1/transactions?limit=9999', headers=headers).status_code == 400


def test_accounts_endpoint(tmp_path, monkeypatch):
    path, client = build(tmp_path)
    secret = 'business-transactions-test-secret-32-chars!'
    monkeypatch.setenv('FINANCE_BUSINESS_TOKEN', secret)
    monkeypatch.setenv('FINANCE_BUSINESS_USER_ID', '1')
    monkeypatch.setenv('FINANCE_BUSINESS_USER_VERSION', '3')
    response = client.get('/api/business/v1/accounts', headers={'Authorization': 'Bearer ' + secret})
    assert response.status_code == 200
    names = [row['name'] for row in response.json['accounts']]
    assert 'First Direct Current' in names and 'Wise Current Account EUR' in names
    assert client.post('/api/business/v1/accounts', headers={'Authorization': 'Bearer ' + secret}).status_code == 405


def test_export_standalone(tmp_path):
    path = tmp_path / 'finance.db'
    with sqlite3.connect(path) as c:
        c.executescript(SCHEMA)
    result = export_transactions(path)
    assert result['contract'] == 'business-transactions-v1'
    assert len(result['transactions']) == 4
