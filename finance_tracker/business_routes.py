"""Optional, read-only remote transport for the Business transactions contract.

Scoped like the Property funding endpoint: a static bearer token from the
environment, pinned to an active user whose auth_version must match, loopback
(or Tailnet-allowed) only, GET requests only. The database is opened read-only;
this integration can never create or modify Finance Tracker data.
"""
import hmac
import os
import sqlite3
from flask import Blueprint, abort, jsonify, request
from .business_export import export_accounts, export_transactions


def create_blueprint(database):
    bp = Blueprint('business_transactions', __name__)

    def authorize(conn):
        secret = os.environ.get('FINANCE_BUSINESS_TOKEN', '')
        if len(secret) < 32 or not hmac.compare_digest(request.headers.get('Authorization', '').encode(), ('Bearer ' + secret).encode()):
            abort(401)
        settings = dict(conn.execute("SELECT key,value FROM settings WHERE key IN ('setup_complete','tailnet_only')"))
        if settings.get('setup_complete') != '1':
            abort(503)
        if settings.get('tailnet_only', '1') == '1' and request.remote_addr not in ('127.0.0.1', '::1'):
            abort(403)
        try:
            uid = int(os.environ.get('FINANCE_BUSINESS_USER_ID', ''))
        except ValueError:
            abort(403)
        user = conn.execute('SELECT active,auth_version,role FROM users WHERE id=?', (uid,)).fetchone()
        if not user or not user['active'] or user['role'] not in ('admin', 'member', 'readonly') or str(user['auth_version']) != os.environ.get('FINANCE_BUSINESS_USER_VERSION', ''):
            abort(403)

    @bp.get('/api/business/v1/transactions')
    def transactions():
        try:
            result = export_transactions(database(), authorize, request.args.get('account_id'),
                                         request.args.get('start'), request.args.get('end'),
                                         request.args.get('min_amount'), request.args.get('max_amount'),
                                         request.args.get('q'), request.args.get('limit', '200'))
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        except (OSError, sqlite3.Error):
            return jsonify(error='Business transaction source unavailable'), 503
        response = jsonify(result)
        response.headers['Cache-Control'] = 'no-store'
        return response

    @bp.get('/api/business/v1/accounts')
    def accounts():
        try:
            result = export_accounts(database(), authorize)
        except (OSError, sqlite3.Error, ValueError):
            return jsonify(error='Business account source unavailable'), 503
        response = jsonify(result)
        response.headers['Cache-Control'] = 'no-store'
        return response

    return bp
