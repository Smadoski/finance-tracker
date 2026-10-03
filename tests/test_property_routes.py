import hashlib
import sqlite3
from flask import Flask
from finance_tracker.property_routes import create_blueprint


def test_remote_contract_is_readonly_and_revocable(tmp_path,monkeypatch):
    path=tmp_path/'finance.db'
    with sqlite3.connect(path) as c:
        c.executescript("CREATE TABLE settings(key TEXT,value TEXT); INSERT INTO settings VALUES('setup_complete','1'),('tailnet_only','1'); CREATE TABLE users(id INTEGER,active INTEGER,auth_version INTEGER,role TEXT); INSERT INTO users VALUES(1,1,3,'readonly'); CREATE TABLE accounts(id INTEGER,name TEXT,institution TEXT,account_type TEXT,currency TEXT,opening_balance REAL,active INTEGER); INSERT INTO accounts VALUES(1,'Premium Bonds','NS&I','premium_bonds','GBP',50000,1); CREATE TABLE transactions(account_id INTEGER,amount REAL); CREATE TABLE valuations(id INTEGER,account_id INTEGER,value REAL,valuation_date TEXT);")
    app=Flask(__name__);app.register_blueprint(create_blueprint(lambda:path));client=app.test_client();url='/api/property/v1/funding'
    secret='readonly-funding-test-secret-32-characters'
    monkeypatch.setenv('FINANCE_PROPERTY_TOKEN',secret);monkeypatch.setenv('FINANCE_PROPERTY_USER_ID','1');monkeypatch.setenv('FINANCE_PROPERTY_USER_VERSION','3')
    headers={'Authorization':'Bearer '+secret};digest=hashlib.sha256(path.read_bytes()).hexdigest()
    assert client.get(url).status_code==401
    response=client.get(url,headers=headers)
    assert response.status_code==200 and response.json['accounts'][0]['balance']=='50000.00'
    assert response.headers['Cache-Control']=='no-store'
    assert client.post(url,headers=headers).status_code==405
    assert client.get(url,headers=headers,environ_overrides={'REMOTE_ADDR':'203.0.113.1'}).status_code==403
    monkeypatch.setenv('FINANCE_PROPERTY_USER_VERSION','2')
    assert client.get(url,headers=headers).status_code==403
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
