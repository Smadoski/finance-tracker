"""Optional, read-only remote transport for the Property funding contract."""
import hmac
import os
import sqlite3
from flask import Blueprint, abort, jsonify, request
from .property_export import export_balances


def create_blueprint(database):
    bp=Blueprint('property_funding',__name__)
    @bp.get('/api/property/v1/funding')
    def accounts():
        secret=os.environ.get('FINANCE_PROPERTY_TOKEN','')
        if len(secret)<32 or not hmac.compare_digest(request.headers.get('Authorization','').encode(),('Bearer '+secret).encode()):abort(401)
        def authorize(conn):
            settings=dict(conn.execute("SELECT key,value FROM settings WHERE key IN ('setup_complete','tailnet_only')"))
            if settings.get('setup_complete')!='1':abort(503)
            if settings.get('tailnet_only','1')=='1' and request.remote_addr not in ('127.0.0.1','::1'):abort(403)
            try:uid=int(os.environ.get('FINANCE_PROPERTY_USER_ID',''))
            except ValueError:abort(403)
            user=conn.execute('SELECT active,auth_version,role FROM users WHERE id=?',(uid,)).fetchone()
            if not user or not user['active'] or user['role'] not in ('admin','member','readonly') or str(user['auth_version'])!=os.environ.get('FINANCE_PROPERTY_USER_VERSION',''):abort(403)
        try:result=export_balances(database(),authorize)
        except (OSError,sqlite3.Error,ValueError):return jsonify(error='Funding source unavailable'),503
        response=jsonify(result);response.headers['Cache-Control']='no-store';return response
    return bp
