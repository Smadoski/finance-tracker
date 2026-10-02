import hashlib
import sqlite3
import pytest
from finance_tracker.property_export import export_balances


def test_export_contract_uses_source_balances_without_writes(tmp_path):
    path=tmp_path/'finance.db'
    with sqlite3.connect(path) as c:
        c.executescript("CREATE TABLE accounts(id INTEGER PRIMARY KEY,name TEXT,institution TEXT,account_type TEXT,currency TEXT,opening_balance REAL,active INTEGER); CREATE TABLE transactions(account_id INTEGER,amount REAL); CREATE TABLE valuations(id INTEGER,account_id INTEGER,value REAL,valuation_date TEXT);")
        for i,(name,kind,currency) in enumerate([('Premium Bonds','premium_bonds','GBP'),('NS&I Bonds','other_asset','GBP'),('First Direct Joint Savings','savings','GBP'),('First Direct ISA','savings','GBP'),('Euro savings','savings','EUR'),('Debt','liability','GBP'),('Card','credit_card','GBP')],1):
            c.execute('INSERT INTO accounts VALUES (?,?,?,?,?,?,1)',(i,name,'Institution',kind,currency,100))
        c.execute('INSERT INTO transactions VALUES (1,25)')
        c.execute("INSERT INTO valuations VALUES (1,2,300,'2026-10-01')")
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    result=export_balances(path)
    assert result['contract']=='property-funding-v1'
    assert len(result['accounts'])==5
    assert result['accounts'][0]['balance']=='125.00'
    assert result['accounts'][1]['balance']=='300.00'
    assert result['accounts'][4]['currency']=='EUR'
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest


def test_missing_database_is_not_created(tmp_path):
    path=tmp_path/'missing.db'
    with pytest.raises(FileNotFoundError): export_balances(path)
    assert not path.exists()
