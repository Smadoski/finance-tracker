from datetime import date

import pytest

from finance_tracker.budgets import period_bounds, target_report


@pytest.mark.parametrize(('period','start','end'),[
    ('weekly',date(2024,5,13),date(2024,5,19)),
    ('monthly',date(2024,5,1),date(2024,5,31)),
    ('quarterly',date(2024,4,1),date(2024,6,30)),
    ('yearly',date(2024,1,1),date(2024,12,31)),
])
def test_target_periods(period,start,end):
    assert period_bounds(period,date(2024,5,15))==(start,end)


def test_parent_subcategory_actuals_and_no_double_count(appmod):
    conn=appmod.db()
    account=conn.execute("INSERT INTO accounts(name,account_type,currency) VALUES('Current','bank','GBP')").lastrowid
    parent=conn.execute("INSERT INTO categories(name,kind) VALUES('Entertainment','expense')").lastrowid
    child=conn.execute("INSERT INTO categories(name,kind,parent_id) VALUES('Drinks','expense',?)",(parent,)).lastrowid
    other=conn.execute("INSERT INTO categories(name,kind,parent_id) VALUES('Cinema','expense',?)",(parent,)).lastrowid
    conn.execute("INSERT INTO transactions(account_id,tx_date,description,amount,category_id) VALUES(?,?,?,?,?)",(account,'2024-05-10','Drinks',-285,child))
    conn.execute("INSERT INTO transactions(account_id,tx_date,description,amount,category_id) VALUES(?,?,?,?,?)",(account,'2024-05-11','Film',-40,other))
    conn.execute("INSERT INTO category_targets(category_id,target_amount,currency,period) VALUES(?,?,?,?)",(parent,400,'GBP','monthly'))
    conn.execute("INSERT INTO category_targets(category_id,target_amount,currency,period) VALUES(?,?,?,?)",(child,250,'GBP','monthly'))
    conn.commit()
    report=target_report(conn,'monthly',date(2024,5,15),'GBP',1.2)
    parent_row=next(r for r in report['rows'] if r['category_id']==parent)
    child_row=next(r for r in report['rows'] if r['category_id']==child)
    assert parent_row['actual']==325 and parent_row['included_in_overall'] is False
    assert child_row['actual']==285 and child_row['status']=='Over target'
    assert child_row['used']==pytest.approx(114)
    assert report['target']==250 and report['actual']==285
    conn.close()


@pytest.mark.parametrize(('actual','status'),[(200,'Under target'),(250,'Exact target'),(285,'Over target')])
def test_target_statuses(appmod,actual,status):
    conn=appmod.db()
    account=conn.execute("INSERT INTO accounts(name,account_type,currency) VALUES('Current','bank','GBP')").lastrowid
    category=conn.execute("SELECT id FROM categories WHERE kind='expense' ORDER BY id LIMIT 1").fetchone()['id']
    conn.execute("INSERT INTO transactions(account_id,tx_date,description,amount,category_id) VALUES(?,?,?,?,?)",(account,'2024-05-10','Spend',-actual,category))
    conn.execute("INSERT INTO category_targets(category_id,target_amount,currency,period) VALUES(?,?,?,?)",(category,250,'GBP','monthly'))
    conn.commit(); report=target_report(conn,'monthly',date(2024,5,15),'GBP',1.2)
    assert report['rows'][0]['status']==status
    conn.close()


def test_target_uses_existing_currency_conversion(appmod):
    conn=appmod.db()
    account=conn.execute("INSERT INTO accounts(name,account_type,currency) VALUES('Euro','bank','EUR')").lastrowid
    category=conn.execute("SELECT id FROM categories WHERE kind='expense' ORDER BY id LIMIT 1").fetchone()['id']
    conn.execute("INSERT INTO transactions(account_id,tx_date,description,amount,category_id) VALUES(?,?,?,?,?)",(account,'2024-05-10','Spend',-120,category))
    conn.execute("INSERT INTO category_targets(category_id,target_amount,currency,period) VALUES(?,?,?,?)",(category,100,'GBP','monthly'))
    conn.commit(); report=target_report(conn,'monthly',date(2024,5,15),'GBP',1.2)
    assert report['actual']==100 and report['status']=='Exact target'
    conn.close()
