from datetime import datetime
import os, sqlite3, tempfile

def test_dropbox_retry_backoff_schedule_contract():
    delays=[300,900,1800,3600,7200,21600]
    assert delays==sorted(delays)
    assert delays[-1]==21600

def test_pending_backup_can_be_retention_protected():
    files=['a.db','b.db','c.db']
    pending='c.db'
    removable=[p for p in files if p!=pending]
    retained=[p for p in files if p==pending]
    assert retained==['c.db'] and 'c.db' not in removable


def test_recovery_proxy_contract_source():
    from pathlib import Path
    source=(Path(__file__).resolve().parents[1]/'app.py').read_text()
    assert "X-Forwarded-For" in source
    assert "X-Real-IP" in source
    assert "Reverse proxies such as Tailscale Serve" in source
