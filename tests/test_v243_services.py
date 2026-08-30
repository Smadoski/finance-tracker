import io
from finance_tracker.receipts import validate_image_content

def test_receipt_magic_rejects_fake_jpeg():
    try: validate_image_content(io.BytesIO(b'not an image'),'receipt.jpg')
    except ValueError: pass
    else: raise AssertionError('fake image accepted')

def test_receipt_magic_accepts_jpeg():
    assert validate_image_content(io.BytesIO(b'\xff\xd8\xff'+b'x'*40),'receipt.jpg')=='.jpg'
