"""Serve synthetic browser fixtures in a temporary copy, never in the working database.
Run with the project Python, then set FINANCE_TEST_URL=http://127.0.0.1:18210.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

SEED = 'import os,sys\nos.environ[\'FINANCE_DISABLE_SCHEDULER\']=\'1\'\nimport app\nfrom datetime import date\nfor key,value in dict(setup_complete=\'1\',auth_required=\'0\',tailnet_only=\'0\',backup_enabled=\'0\',fx_auto=\'0\',household_name=\'Finance Tracker preview\').items():app.set_setting(key,value)\nc=app.db()\nif not c.execute(\'SELECT 1 FROM accounts\').fetchone():\n for name,kind,currency,balance,asset in [(\'First Direct\',\'current\',\'GBP\',5240,\'accessible\'),(\'Bank of Cyprus\',\'current\',\'EUR\',8310,\'designated\'),(\'Everyday card\',\'credit_card\',\'GBP\',425,\'unclassified\'),(\'Pension\',\'pension\',\'GBP\',32000,\'retirement\')]:\n  c.execute(\'INSERT INTO accounts(name,account_type,currency,opening_balance,asset_class) VALUES(?,?,?,?,?)\',(name,kind,currency,balance,asset))\n cat=c.execute("SELECT id FROM categories WHERE kind=\'expense\' LIMIT 1").fetchone()[0]\n for i in range(8):c.execute(\'INSERT INTO transactions(account_id,tx_date,description,amount,category_id,expense_type) VALUES(?,?,?,?,?,?)\',(1,date.today().isoformat(),[\'Groceries\',\'Electricity\',\'Coffee\'][i%3],-12.5*(i+1),cat,\'normal\'))\n c.execute("INSERT INTO pending_transactions(account_id,tx_date,description,amount,entry_type) VALUES(3,?,\'Pending card purchase\',-25,\'expense\')",(date.today().isoformat(),))\n c.execute("INSERT INTO recurring_rules(description,transaction_type,account_id,amount,category_id,start_date,next_scheduled_date,frequency,expense_type) VALUES(\'Monthly subscription\',\'expense\',3,20,?,?,?,\'monthly\',\'normal\')",(cat,date.today().isoformat(),date.today().isoformat()))\n c.execute("INSERT INTO recurring_rules(description,transaction_type,account_id,to_account_id,amount,to_amount,start_date,next_scheduled_date,frequency) VALUES(\'Card repayment\',\'transfer\',1,3,100,100,?,?,\'monthly\')",(date.today().isoformat(),date.today().isoformat()))\n c.execute("INSERT INTO recurring_rules(description,transaction_type,account_id,amount,start_date,next_scheduled_date,frequency,income_type) VALUES(\'Interest\',\'income\',1,50,?,?,\'monthly\',\'investment\')",(date.today().isoformat(),date.today().isoformat()))\n c.execute("INSERT INTO funding_strategies(purpose,kind,currency,monthly_amount) VALUES(\'Housing\',\'housing\',\'EUR\',900)")\n c.execute(\'INSERT INTO funding_steps(strategy_id,position,account_id) VALUES(1,0,2)\')\n c.commit()\nc.close();app.set_setting(\'dashboard_account_1_id\',\'1\');app.set_setting(\'dashboard_account_2_id\',\'2\')\napp.app.run(host=\'127.0.0.1\',port=18210,debug=False)\n'

if __name__ == '__main__':
    source=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='finance-browser-') as work:
        shutil.copytree(source,work,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.git','.venv','data','wheelhouse','__pycache__','.pytest_cache','*.pkg','*.zip'))
        subprocess.run([sys.executable,'-c',SEED],cwd=work,env=dict(os.environ,FINANCE_DISABLE_SCHEDULER='1'),check=True)
