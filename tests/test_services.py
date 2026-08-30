import sqlite3
from finance_tracker.categories import save_category_parent, selector_groups
from finance_tracker.money import convert, dual_values
from finance_tracker.reports import display_report_values

def make_db():
    conn=sqlite3.connect(":memory:")
    conn.row_factory=sqlite3.Row
    conn.executescript("""
    CREATE TABLE categories(id INTEGER PRIMARY KEY,name TEXT,kind TEXT,parent_id INTEGER);
    INSERT INTO categories VALUES(1,'Motoring','expense',NULL);
    INSERT INTO categories VALUES(2,'Petrol','expense',NULL);
    """)
    return conn

def test_category_parent_persistence_and_selector():
    conn=make_db()
    ok,_=save_category_parent(conn,2,1)
    assert ok
    assert conn.execute("SELECT parent_id FROM categories WHERE id=2").fetchone()["parent_id"] == 1
    group=next(g for g in selector_groups(conn) if g["name"]=="Motoring")
    assert group["is_parent"] is True
    assert [c["name"] for c in group["children"]] == ["Petrol"]

def test_money_conversion_compatibility():
    assert convert(100,"GBP","EUR",1.2) == 120
    assert dual_values(120,"EUR",1.2) == (100,120)

def test_expense_report_display_is_positive():
    assert display_report_values(-10,"GBP",1.2,"expense",dual_values) == (10,12)
