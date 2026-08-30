import os, uuid

MAGIC={
 "jpg":lambda h:h.startswith(b"\xff\xd8\xff"),
 "png":lambda h:h.startswith(b"\x89PNG\r\n\x1a\n"),
 "tiff":lambda h:h.startswith(b"II*\x00") or h.startswith(b"MM\x00*"),
 "heic":lambda h:len(h)>=12 and h[4:8]==b"ftyp" and any(x in h[8:32] for x in (b"heic",b"heix",b"hevc",b"hevx",b"mif1")),
}
EXT_KIND={".jpg":"jpg",".jpeg":"jpg",".png":"png",".tif":"tiff",".tiff":"tiff",".heic":"heic",".heif":"heic"}

def validate_image_content(stream,filename):
    ext=os.path.splitext(filename or "")[1].lower(); kind=EXT_KIND.get(ext)
    if not kind: raise ValueError("Receipt must be a JPG, PNG, HEIC or TIFF image.")
    pos=stream.tell() if hasattr(stream,"tell") else None; head=stream.read(64)
    if pos is not None: stream.seek(pos)
    if not MAGIC[kind](head): raise ValueError("The uploaded receipt content does not match a supported image type.")
    return ext

def save_receipt(upload,receipt_dir):
    if not upload or not getattr(upload,"filename",None): return None
    ext=validate_image_content(upload.stream,upload.filename); filename=f"{uuid.uuid4().hex}{ext}"
    os.makedirs(receipt_dir,exist_ok=True); upload.save(os.path.join(receipt_dir,filename)); return filename

def delete_if_unreferenced(conn,receipt_dir,filename):
    if not filename:return False
    tx=conn.execute("SELECT COUNT(*) n FROM transactions WHERE receipt_path=?",(filename,)).fetchone()["n"]
    pd=conn.execute("SELECT COUNT(*) n FROM pending_transactions WHERE receipt_path=?",(filename,)).fetchone()["n"]
    if tx or pd:return False
    path=os.path.join(receipt_dir,filename)
    if os.path.isfile(path): os.remove(path); return True
    return False
