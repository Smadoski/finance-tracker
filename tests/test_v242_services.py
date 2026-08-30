import io,sqlite3
from finance_tracker.receipts import validate_image_content,delete_if_unreferenced
from finance_tracker.categories import save_category_parent
def test_receipt_magic_rejects_renamed_file():
    try:validate_image_content(io.BytesIO(b'not image'),'x.jpg')
    except ValueError:pass
    else:raise AssertionError('accepted bad content')
def test_receipt_magic_accepts_jpeg():assert validate_image_content(io.BytesIO(b'\xff\xd8\xff'+b'x'*40),'x.jpg')=='.jpg'
def test_category_parent_readback():
    c=sqlite3.connect(':memory:'); c.row_factory=sqlite3.Row; c.executescript("CREATE TABLE categories(id INTEGER PRIMARY KEY,name TEXT,kind TEXT,parent_id INTEGER); INSERT INTO categories VALUES(1,'Motoring','expense',NULL); INSERT INTO categories VALUES(2,'Petrol','expense',NULL);"); ok,_=save_category_parent(c,2,1); assert ok and c.execute('SELECT parent_id FROM categories WHERE id=2').fetchone()['parent_id']==1
