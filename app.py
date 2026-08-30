from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, send_from_directory, abort
import sqlite3, os, secrets, io, re, uuid, urllib.request, ssl, xml.etree.ElementTree as ET, subprocess, shutil, json, sys, time
from finance_tracker.database import connect as db_connect
from finance_tracker.categories import save_category_parent as category_save_parent, selector_groups as service_category_selector_groups
from finance_tracker.money import convert as money_convert, dual_values as money_dual_values
from finance_tracker.reports import display_report_values
from finance_tracker.settings import security_summary as build_security_summary
from finance_tracker.receipts import save_receipt as receipt_save, delete_if_unreferenced
from finance_tracker.accounts import account_balance as service_account_balance
import certifi
from datetime import date, datetime
from calendar import monthrange
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import mm

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, 'finance.db')
RECEIPT_DIR = os.path.join(DATA_DIR, 'receipts')
os.makedirs(RECEIPT_DIR, exist_ok=True)

app = Flask(__name__)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', MAX_CONTENT_LENGTH=15*1024*1024)
version_path=os.path.join(APP_DIR,'VERSION')
try:
    APP_VERSION=open(version_path,encoding='utf-8').read().strip()
except OSError:
    APP_VERSION='2.1.0'
secret_path = os.path.join(DATA_DIR, '.secret_key')
if os.path.exists(secret_path):
    with open(secret_path, 'rb') as f: app.secret_key = f.read()
else:
    key = secrets.token_bytes(32)
    with open(secret_path, 'wb') as f: f.write(key)
    app.secret_key = key


def db():
    return db_connect(DB_PATH)


def init_db():
    database_existed = os.path.exists(DB_PATH)
    conn = db()
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'member',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        account_type TEXT NOT NULL,
        currency TEXT NOT NULL CHECK(currency IN ('GBP','EUR')),
        opening_balance REAL NOT NULL DEFAULT 0,
        institution TEXT,
        notes TEXT,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        kind TEXT NOT NULL DEFAULT 'expense' CHECK(kind IN ('income','expense','transfer','other')),
        parent_id INTEGER REFERENCES categories(id) ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    );
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
        tx_date TEXT NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        category_id INTEGER REFERENCES categories(id),
        tag_text TEXT,
        notes TEXT,
        transfer_group TEXT,
        created_by INTEGER REFERENCES users(id),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS pending_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
        tx_date TEXT NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        category_id INTEGER REFERENCES categories(id),
        notes TEXT,
        receipt_path TEXT,
        ocr_text TEXT,
        created_by INTEGER REFERENCES users(id),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS valuations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
        valuation_date TEXT NOT NULL,
        value REAL NOT NULL,
        notes TEXT,
        created_by INTEGER REFERENCES users(id),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(account_id, valuation_date)
    );
    CREATE TABLE IF NOT EXISTS fx_rates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rate_date TEXT NOT NULL,
        gbp_to_eur REAL NOT NULL,
        UNIQUE(rate_date)
    );
    ''')
    # Lightweight in-place migrations for existing databases.
    cat_cols={r['name'] for r in conn.execute('PRAGMA table_info(categories)').fetchall()}
    if 'parent_id' not in cat_cols:
        conn.execute('ALTER TABLE categories ADD COLUMN parent_id INTEGER REFERENCES categories(id) ON DELETE SET NULL')
    tx_cols={r['name'] for r in conn.execute('PRAGMA table_info(transactions)').fetchall()}
    if 'receipt_path' not in tx_cols:
        conn.execute('ALTER TABLE transactions ADD COLUMN receipt_path TEXT')
    fx_cols={r['name'] for r in conn.execute('PRAGMA table_info(fx_rates)').fetchall()}
    if 'source' not in fx_cols:
        conn.execute('ALTER TABLE fx_rates ADD COLUMN source TEXT')
    user_cols={r['name'] for r in conn.execute('PRAGMA table_info(users)').fetchall()}
    if 'active' not in user_cols:
        conn.execute('ALTER TABLE users ADD COLUMN active INTEGER NOT NULL DEFAULT 1')
    if 'auth_version' not in user_cols:
        conn.execute('ALTER TABLE users ADD COLUMN auth_version INTEGER NOT NULL DEFAULT 1')
    pending_cols={r['name'] for r in conn.execute('PRAGMA table_info(pending_transactions)').fetchall()}
    if 'entry_type' not in pending_cols:
        conn.execute("ALTER TABLE pending_transactions ADD COLUMN entry_type TEXT NOT NULL DEFAULT 'expense'")
        conn.execute("UPDATE pending_transactions SET entry_type=CASE WHEN amount<0 THEN 'expense' ELSE 'income' END")
    defaults = {
        'base_currency':'GBP','household_name':'Household Finance','fx_auto':'1','quick_account_id':'',
        'dashboard_account_1_id':'','dashboard_account_2_id':'',
        'backup_enabled':'1','backup_location':'','backup_frequency':'daily','backup_retention':'10','backup_last_date':'','backup_last_status':'Never',
        'dropbox_enabled':'0','dropbox_folder':'FinanceTracker','dropbox_last_status':'Not tested','dropbox_last_success_date':'','dropbox_pending_path':'','dropbox_retry_count':'0','dropbox_next_retry':'',
        'licensed_to':'','licence_number':'','fx_last_check':'','fx_last_status':'Not checked yet',
        'auth_required':'0','tailnet_only':'1','setup_complete':'1' if database_existed else '0'
    }
    for k,v in defaults.items():
        conn.execute('INSERT OR IGNORE INTO settings(key,value) VALUES (?,?)',(k,v))
    for name, kind in [
        ('Pension Income','income'),('Savings Interest','income'),('Premium Bond Prize','income'),
        ('Salary','income'),('Groceries','expense'),('Electricity','expense'),('Water','expense'),
        ('Internet','expense'),('Fuel','expense'),('Eating Out','expense'),('Medical','expense'),
        ('Insurance','expense'),('Travel','expense'),('Household','expense'),('Transfer','transfer')
    ]:
        conn.execute('INSERT OR IGNORE INTO categories(name,kind) VALUES (?,?)',(name,kind))
    conn.commit(); conn.close()

init_db()


def get_setting(key, default=None):
    conn=db(); r=conn.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone(); conn.close()
    return r['value'] if r else default


def set_setting(key,value):
    conn=db(); conn.execute('INSERT INTO settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,str(value))); conn.commit(); conn.close()


def authentication_enabled():
    return get_setting('auth_required','0') == '1'

def tailnet_only_enabled():
    return get_setting('tailnet_only','1') == '1'

def setup_complete():
    return get_setting('setup_complete','1') == '1'


def local_request_only():
    remote=(request.remote_addr or '')
    if remote not in ('127.0.0.1','::1'):
        return False
    # Reverse proxies such as Tailscale Serve connect to Flask over loopback.
    # A forwarded client address means the request is not truly local-console access.
    forwarded=(request.headers.get('X-Forwarded-For','') or request.headers.get('X-Real-IP','')).strip()
    if forwarded:
        first=forwarded.split(',')[0].strip()
        if first not in ('127.0.0.1','::1'):
            return False
    return True


def current_user():
    if not authentication_enabled():
        # Use a real administrator for audit attribution when one exists.
        # If no user exists (e.g. a clean no-login install), return a local
        # administrative identity with id=None; nullable created_by fields then
        # remain valid without forcing initial account creation/sign-in.
        conn=db()
        u=conn.execute("SELECT * FROM users WHERE COALESCE(active,1)=1 ORDER BY CASE WHEN role='admin' THEN 0 ELSE 1 END,id LIMIT 1").fetchone()
        conn.close()
        return u if u else {'id':None,'name':'Local User','username':'local','role':'admin'}
    if not session.get('user_id'):
        return None
    conn=db()
    u=conn.execute('SELECT * FROM users WHERE id=? AND COALESCE(active,1)=1',(session['user_id'],)).fetchone()
    conn.close()
    if not u:
        session.clear()
        return None
    if session.get('auth_version',1) != u['auth_version']:
        session.clear()
        return None
    return u


def login_required(fn):
    @wraps(fn)
    def wrapper(*a,**kw):
        if not authentication_enabled():
            return fn(*a,**kw)
        if not current_user():
            return redirect(url_for('login'))
        return fn(*a,**kw)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*a,**kw):
        if not authentication_enabled():
            return fn(*a,**kw)
        u=current_user()
        if not u:
            return redirect(url_for('login'))
        if u['role']!='admin':
            abort(403)
        return fn(*a,**kw)
    return wrapper


def csrf_token():
    if 'csrf' not in session: session['csrf']=secrets.token_hex(16)
    return session['csrf']

@app.context_processor
def inject_globals():
    return dict(current_user=current_user(), csrf_token=csrf_token(), household_name=get_setting('household_name','Household Finance'), app_version=APP_VERSION, auth_required=get_setting('auth_required','1'))

@app.before_request
def access_guard():
    if setup_complete() and request.endpoint not in ('static','setup'):
        try: maybe_automatic_backup()
        except Exception as e: set_setting('backup_last_status',f'Backup failed: {e}')
    if not setup_complete() and request.endpoint not in ('setup','static'):
        return redirect(url_for('setup'))
    if tailnet_only_enabled() and (request.remote_addr or '') not in ('127.0.0.1','::1'):
        abort(403, 'Finance Tracker is configured for Tailnet-only access.')

@app.before_request
def cookie_security():
    app.config['SESSION_COOKIE_SECURE'] = request.is_secure or request.headers.get('X-Forwarded-Proto','').lower()=='https'


@app.before_request
def readonly_guard():
    if request.method in ('POST','PUT','PATCH','DELETE') and authentication_enabled():
        u=current_user()
        if u and u['role']=='readonly':
            abort(403, 'This account is Read Only.')


@app.before_request
def csrf_protect():
    if request.method == 'POST':
        if request.form.get('_csrf') != session.get('csrf'):
            abort(400, 'Invalid security token')



def category_rows(conn, kinds=None):
    params=[]; where=''
    if kinds:
        qs=','.join('?' for _ in kinds); where=f'WHERE c.kind IN ({qs})'; params=list(kinds)
    return conn.execute(f"""SELECT c.*,p.name parent_name,p.kind parent_kind,
                                   (SELECT COUNT(*) FROM categories ch WHERE ch.parent_id=c.id) child_count
                            FROM categories c
                            LEFT JOIN categories p ON p.id=c.parent_id
                            {where}
                            ORDER BY c.kind,
                                     COALESCE(p.name,c.name),
                                     CASE WHEN c.parent_id IS NULL THEN 0 ELSE 1 END,
                                     c.name""",params).fetchall()

def category_label(row):
    return f"{row['parent_name']} / {row['name']}" if row['parent_name'] else row['name']

def category_options(conn, kinds=None):
    items=[]
    for r in category_rows(conn,kinds):
        item=dict(r)
        parent_id=item.get('parent_id')
        child_count=int(item.get('child_count') or 0)
        item['parent_id']=int(parent_id) if parent_id not in (None,'') else None
        item['child_count']=child_count
        item['label']=f"{item.get('parent_name')} / {item.get('name')}" if item.get('parent_name') else item.get('name')
        item['is_subcategory']=item['parent_id'] is not None
        item['is_parent']=item['parent_id'] is None and child_count > 0
        item['role']='subcategory' if item['is_subcategory'] else ('parent' if item['is_parent'] else 'category')
        items.append(item)
    return items

def category_selector_groups(conn, kinds=None):
    groups = service_category_selector_groups(conn)
    if kinds:
        return [g for g in groups if g["kind"] in kinds]
    return groups


def backup_root():
    configured=get_setting('backup_location','').strip()
    return os.path.expanduser(configured) if configured else os.path.expanduser('~/Library/Application Support/Adams-Home/Finance Tracker/Backups')

def create_local_backup():
    if not os.path.exists(DB_PATH): return False,'Database not found.',None
    target=backup_root(); os.makedirs(target,exist_ok=True); stamp=datetime.now().strftime('%Y%m%d-%H%M%S'); dest=os.path.join(target,f'finance-{stamp}.db')
    source=sqlite3.connect(DB_PATH)
    try:
        destination=sqlite3.connect(dest)
        try: source.backup(destination)
        finally: destination.close()
    finally: source.close()
    try: keep=max(1,int(get_setting('backup_retention','10') or '10'))
    except ValueError: keep=10
    files=sorted([os.path.join(target,n) for n in os.listdir(target) if n.startswith('finance-') and n.endswith('.db')],key=os.path.getmtime,reverse=True)
    pending=os.path.abspath(get_setting('dropbox_pending_path','').strip()) if get_setting('dropbox_pending_path','').strip() else ''
    removable=[p for p in files if not pending or os.path.abspath(p)!=pending]
    retained=[p for p in files if pending and os.path.abspath(p)==pending]
    allowed=max(0,keep-len(retained))
    for old in removable[allowed:]:
        try: os.remove(old)
        except OSError: pass
    set_setting('backup_last_date',date.today().isoformat()); set_setting('backup_last_status',f'Completed {datetime.now().isoformat(timespec="seconds")}')
    return True,'Backup completed.',dest

def set_dropbox_token(token):
    token=(token or '').strip()
    if not token:return
    if sys.platform!='darwin': raise RuntimeError('Secure Dropbox token storage is currently supported on macOS only.')
    subprocess.run(['/usr/bin/security','delete-generic-password','-s','Adams-Home Finance Tracker Dropbox','-a','FinanceTracker'],capture_output=True)
    cp=subprocess.run(['/usr/bin/security','add-generic-password','-U','-s','Adams-Home Finance Tracker Dropbox','-a','FinanceTracker','-w',token],capture_output=True,text=True)
    if cp.returncode!=0: raise RuntimeError('Unable to save Dropbox token in macOS Keychain.')

def get_dropbox_token():
    if sys.platform!='darwin': return ''
    cp=subprocess.run(['/usr/bin/security','find-generic-password','-s','Adams-Home Finance Tracker Dropbox','-a','FinanceTracker','-w'],capture_output=True,text=True)
    return cp.stdout.strip() if cp.returncode==0 else ''

def dropbox_request(endpoint,payload=None,content=None):
    token=get_dropbox_token()
    if not token: raise RuntimeError('Dropbox access token is not configured in macOS Keychain.')
    headers={'Authorization':'Bearer '+token}
    if content is None:
        headers['Content-Type']='application/json'; data=json.dumps(payload or {}).encode(); url='https://api.dropboxapi.com/2/'+endpoint
    else:
        headers['Content-Type']='application/octet-stream'; headers['Dropbox-API-Arg']=json.dumps(payload or {}); data=content; url='https://content.dropboxapi.com/2/'+endpoint
    req=urllib.request.Request(url,data=data,headers=headers,method='POST')
    with urllib.request.urlopen(req,timeout=20) as resp: raw=resp.read()
    return json.loads(raw.decode()) if raw else {}

def test_dropbox_connection():
    try:
        info=dropbox_request('users/get_current_account',{}); who=((info.get('name') or {}).get('display_name')) or info.get('email') or 'Dropbox account'; set_setting('dropbox_last_status',f'Connected: {who}'); return True,f'Connected to {who}.'
    except Exception as e:
        set_setting('dropbox_last_status',f'Connection failed: {e}'); return False,f'Dropbox connection failed: {e}'

def upload_backup_to_dropbox(path):
    folder=(get_setting('dropbox_folder','FinanceTracker') or 'FinanceTracker').strip('/ ')
    remote='/' + ((folder + '/') if folder else '') + os.path.basename(path)
    with open(path,'rb') as f:
        content=f.read()
    dropbox_request('files/upload',{'path':remote,'mode':'add','autorename':True,'mute':False},content)
    set_setting('dropbox_last_status',f'Uploaded {datetime.now().isoformat(timespec="seconds")}')
    set_setting('dropbox_last_success_date',date.today().isoformat())
    set_setting('dropbox_pending_path','')
    set_setting('dropbox_retry_count','0')
    set_setting('dropbox_next_retry','')
    return True,'Backup uploaded to Dropbox.'

def create_dropbox_backup():
    ok,msg,path=create_local_backup()
    if not ok:return False,msg
    try:return upload_backup_to_dropbox(path)
    except Exception as e:set_setting('dropbox_last_status',f'Upload failed: {e}'); return False,f'Dropbox backup failed: {e}'

def schedule_dropbox_retry(path, error):
    try:
        count=max(0,int(get_setting('dropbox_retry_count','0') or '0'))+1
    except ValueError:
        count=1
    # Backoff: 5m, 15m, 30m, 1h, 2h, capped at 6h.
    delays=[300,900,1800,3600,7200,21600]
    delay=delays[min(count-1,len(delays)-1)]
    next_retry=datetime.now().timestamp()+delay
    set_setting('dropbox_pending_path',path)
    set_setting('dropbox_retry_count',str(count))
    set_setting('dropbox_next_retry',str(int(next_retry)))
    set_setting('dropbox_last_status',f'Upload failed; retry {count} scheduled. {error}')


def dropbox_retry_due():
    raw=get_setting('dropbox_next_retry','').strip()
    if not raw:
        return True
    try:
        return time.time() >= float(raw)
    except ValueError:
        return True


def maybe_automatic_backup():
    if get_setting('backup_enabled','1')!='1':
        return
    last=get_setting('backup_last_date','')
    freq=get_setting('backup_frequency','daily')
    today=date.today()
    try:
        last_date=datetime.strptime(last,'%Y-%m-%d').date() if last else None
    except ValueError:
        last_date=None
    due=last_date is None
    if last_date:
        days=(today-last_date).days
        due=(freq=='daily' and days>=1) or (freq=='weekly' and days>=7) or (freq=='monthly' and days>=28)
    if due:
        ok,msg,path=create_local_backup()
        if ok and get_setting('dropbox_enabled','0')=='1':
            try:
                upload_backup_to_dropbox(path)
            except Exception as exc:
                schedule_dropbox_retry(path,exc)
    if get_setting('dropbox_enabled','0')=='1':
        pending=get_setting('dropbox_pending_path','').strip()
        if pending and os.path.isfile(pending) and dropbox_retry_due():
            try:
                upload_backup_to_dropbox(pending)
            except Exception as exc:
                schedule_dropbox_retry(pending,exc)


def tailscale_status():
    exe=shutil.which('tailscale')
    if not exe and os.path.exists('/Applications/Tailscale.app/Contents/MacOS/Tailscale'):
        exe='/Applications/Tailscale.app/Contents/MacOS/Tailscale'
    if not exe:
        return {'healthy':False,'detail':'Tailscale CLI not found','url':''}
    try:
        cp=subprocess.run([exe,'status','--json'],capture_output=True,text=True,timeout=3)
        if cp.returncode!=0:
            return {'healthy':False,'detail':'Tailscale is installed but not connected','url':''}
        data=json.loads(cp.stdout or '{}'); dns=(data.get('Self') or {}).get('DNSName','').rstrip('.')
        return {'healthy':True,'detail':'Connected to Tailnet','url':f'https://{dns}:8443' if dns else ''}
    except Exception:
        return {'healthy':False,'detail':'Unable to read Tailscale status','url':''}

def account_balance(conn, account):
    return service_account_balance(conn, account)

def latest_fx(conn):
    r=conn.execute('SELECT gbp_to_eur FROM fx_rates ORDER BY rate_date DESC,id DESC LIMIT 1').fetchone()
    return float(r['gbp_to_eur']) if r else 1.15


def convert(value, currency, base, fx):
    return money_convert(value, currency, base, fx)

def dual_values(value, currency, fx):
    return money_dual_values(value, currency, fx)


def month_bounds(d=None):
    d=d or date.today()
    return d.replace(day=1).isoformat(), d.replace(day=monthrange(d.year,d.month)[1]).isoformat()

def safe_date(value, fallback):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date().isoformat()
    except (TypeError, ValueError):
        return fallback


def refresh_fx_rate(force=False):
    '''Fetch the ECB daily reference rate. Returns (success, message).'''
    if get_setting('fx_auto','1') != '1' and not force:
        return False, 'Automatic exchange-rate updates are disabled.'
    today=date.today().isoformat()
    if not force and get_setting('fx_last_check','') == today:
        return True, get_setting('fx_last_status','Already checked today')
    try:
        req=urllib.request.Request(
            'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml',
            headers={'User-Agent':'HouseholdFinanceTracker/2.0'}
        )
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(req, timeout=4, context=ssl_context) as response:
            root=ET.fromstring(response.read())
        rate_date=None; gbp_per_eur=None
        for node in root.iter():
            if node.attrib.get('time'):
                rate_date=node.attrib['time']
            if node.attrib.get('currency') == 'GBP':
                gbp_per_eur=float(node.attrib['rate'])
        if not rate_date or not gbp_per_eur:
            raise ValueError('GBP reference rate was not present in the ECB response')
        gbp_to_eur=1.0/gbp_per_eur
        conn=db()
        conn.execute('''INSERT INTO fx_rates(rate_date,gbp_to_eur,source) VALUES (?,?,?)
                        ON CONFLICT(rate_date) DO UPDATE SET gbp_to_eur=excluded.gbp_to_eur,source=excluded.source''',
                     (rate_date,gbp_to_eur,'ECB'))
        conn.commit(); conn.close()
        msg=f'ECB rate updated: £1 = €{gbp_to_eur:.4f} ({rate_date})'
        set_setting('fx_last_check',today); set_setting('fx_last_status',msg)
        return True,msg
    except Exception as exc:
        msg=f'Automatic rate update failed; using the last saved rate. {type(exc).__name__}: {exc}'
        set_setting('fx_last_check',today); set_setting('fx_last_status',msg)
        return False,msg


def save_receipt(upload):
    return receipt_save(upload, RECEIPT_DIR)


def ocr_receipt(filename):
    '''Use Apple's on-device Vision OCR via PyObjC. No cloud receipt data is sent.'''
    if not filename:
        return ''
    try:
        import Vision
        from Foundation import NSURL
        path=os.path.join(RECEIPT_DIR,filename)
        url=NSURL.fileURLWithPath_(path)
        request_obj=Vision.VNRecognizeTextRequest.alloc().init()
        request_obj.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
        request_obj.setUsesLanguageCorrection_(True)
        try:
            request_obj.setRecognitionLanguages_(['en-GB','en-US'])
        except Exception:
            pass
        handler=Vision.VNImageRequestHandler.alloc().initWithURL_options_(url,{})
        result=handler.performRequests_error_([request_obj],None)
        if isinstance(result,tuple):
            ok,error=result
        else:
            ok,error=result,None
        if not ok:
            raise RuntimeError(str(error))
        lines=[]
        for observation in request_obj.results() or []:
            candidates=observation.topCandidates_(1)
            if candidates:
                lines.append(str(candidates[0].string()))
        return '\n'.join(lines).strip()
    except ImportError as exc:
        raise RuntimeError('Apple Vision OCR support is not installed. Run pip install -r requirements.txt after updating.') from exc


def suggest_category(conn, description, ocr_text=''):
    text=f'{description} {ocr_text}'.lower()
    # First learn from prior descriptions/merchants already categorised by the household.
    if description.strip():
        escaped=description.strip().lower().replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
        row=conn.execute('''SELECT category_id,COUNT(*) n FROM transactions
                            WHERE category_id IS NOT NULL AND lower(description) LIKE ? ESCAPE '\\'
                            GROUP BY category_id ORDER BY n DESC LIMIT 1''',('%'+escaped+'%',)).fetchone()
        if row: return row['category_id']
    keyword_map=[
        (('restaurant','taverna','cafe','coffee','bar','pub','grill','pizza','burger','fish','kebab'),'Eating Out'),
        (('supermarket','lidl','alphamega','papantoniou','philippos','grocery','market'),'Groceries'),
        (('petrol','fuel','esso','shell','petrolina','eac petrol'),'Fuel'),
        (('pharmacy','chemist','medical','doctor','clinic','hospital'),'Medical'),
        (('electricity','eac'),'Electricity'),(('water board','water'),'Water'),
        (('internet','cyta','cablenet'),'Internet'),(('airways','airline','flight','hotel','taxi'),'Travel')]
    for words,cat_name in keyword_map:
        if any(word in text for word in words):
            row=conn.execute('SELECT id FROM categories WHERE name=?',(cat_name,)).fetchone()
            if row: return row['id']
    return None


def parse_receipt_text(conn, text):
    lines=[x.strip() for x in text.splitlines() if x.strip()]
    description=lines[0][:120] if lines else ''
    tx_date=date.today().isoformat()
    for line in lines:
        m=re.search(r'\b(\d{1,2})[\-/\.](\d{1,2})[\-/\.](\d{2,4})\b',line)
        if m:
            d,mth,y=map(int,m.groups()); y=y+2000 if y<100 else y
            try: tx_date=date(y,mth,d).isoformat(); break
            except ValueError: pass
    candidates=[]
    total_candidates=[]
    money_re=re.compile(r'(?:€|EUR\s*)?(-?\d{1,5}(?:[.,]\d{2}))\b',re.I)
    for idx,line in enumerate(lines):
        vals=[]
        for match in money_re.findall(line.replace(' ','')):
            try: vals.append(float(match.replace(',','.')))
            except ValueError: pass
        for value in vals: candidates.append(value)
        if re.search(r'\b(total|amount due|balance due|grand total)\b',line,re.I) and vals:
            total_candidates.extend(vals)
    amount=(total_candidates[-1] if total_candidates else (max(candidates) if candidates else 0.0))
    category_id=suggest_category(conn,description,text)
    return {'tx_date':tx_date,'description':description,'amount':amount,'category_id':category_id}

LOGIN_ATTEMPTS={}
LOGIN_WINDOW_SECONDS=300
LOGIN_MAX_ATTEMPTS=5

def login_rate_key(username):
    return f"{(request.remote_addr or 'unknown')}|{(username or '').strip().lower()}"

def login_rate_limited(username):
    key=login_rate_key(username); now=time.time(); attempts=[t for t in LOGIN_ATTEMPTS.get(key,[]) if now-t<LOGIN_WINDOW_SECONDS]; LOGIN_ATTEMPTS[key]=attempts; return len(attempts)>=LOGIN_MAX_ATTEMPTS

def record_login_failure(username): LOGIN_ATTEMPTS.setdefault(login_rate_key(username),[]).append(time.time())
def clear_login_failures(username): LOGIN_ATTEMPTS.pop(login_rate_key(username),None)

@app.route('/setup', methods=['GET','POST'])
def setup():
    if not setup_complete():
        ts=tailscale_status()
        if request.method=='POST':
            use_tailnet=request.form.get('tailnet_only')=='1'; use_auth=request.form.get('auth_required')=='1'
            if not use_tailnet and not use_auth and request.form.get('confirm_unprotected')!='1':
                flash('Confirm the unprotected-access warning.','error'); return render_template('first_setup.html',tailscale=ts)
            if use_auth:
                name=request.form.get('name','').strip(); username=request.form.get('username','').strip().lower(); password=request.form.get('password','')
                if not name or not username or len(password)<10:
                    flash('Credentials require a name, username and password of at least 10 characters.','error'); return render_template('first_setup.html',tailscale=ts)
                conn=db(); conn.execute('INSERT INTO users(name,username,password_hash,role) VALUES (?,?,?,?)',(name,username,generate_password_hash(password),'admin')); conn.commit(); conn.close()
            set_setting('tailnet_only','1' if use_tailnet else '0'); set_setting('auth_required','1' if use_auth else '0'); set_setting('setup_complete','1')
            flash('Initial security configuration saved.','ok'); return redirect(url_for('login') if use_auth else url_for('dashboard'))
        return render_template('first_setup.html',tailscale=ts)
    if not authentication_enabled(): return redirect(url_for('dashboard'))
    if not local_request_only():
        abort(403, 'Administrator recovery is available only from the Finance Tracker host.')
    conn=db(); active_admins=conn.execute("SELECT COUNT(*) c FROM users WHERE role='admin' AND COALESCE(active,1)=1").fetchone()['c']
    if active_admins: conn.close(); return redirect(url_for('login'))
    if request.method=='POST':
        name=request.form['name'].strip(); username=request.form['username'].strip().lower(); password=request.form['password']
        if len(password)<10: flash('Use a password of at least 10 characters.','error')
        else:
            existing=conn.execute('SELECT id FROM users WHERE username=?',(username,)).fetchone()
            if existing:
                conn.execute("UPDATE users SET name=?,password_hash=?,role='admin',active=1,auth_version=auth_version+1 WHERE id=?",(name,generate_password_hash(password),existing['id']))
            else:
                conn.execute('INSERT INTO users(name,username,password_hash,role,active,auth_version) VALUES (?,?,?,?,1,1)',(name,username,generate_password_hash(password),'admin'))
            conn.commit(); conn.close(); flash('Administrator account created or recovered. Please sign in.','ok'); return redirect(url_for('login'))
    conn.close(); return render_template('setup.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if not authentication_enabled(): return redirect(url_for('dashboard'))
    conn=db()
    if conn.execute("SELECT COUNT(*) c FROM users WHERE role='admin' AND COALESCE(active,1)=1").fetchone()['c']==0:
        conn.close(); return redirect(url_for('setup'))
    if request.method=='POST':
        username=request.form.get('username','').strip().lower()
        if login_rate_limited(username):
            conn.close(); flash('Too many unsuccessful sign-in attempts. Try again in a few minutes.','error'); return render_template('login.html'),429
        u=conn.execute('SELECT * FROM users WHERE username=? AND COALESCE(active,1)=1',(username,)).fetchone()
        if u and check_password_hash(u['password_hash'],request.form.get('password','')):
            clear_login_failures(username); session.clear(); session['user_id']=u['id']; session['auth_version']=u['auth_version']; csrf_token(); conn.close(); return redirect(url_for('dashboard'))
        record_login_failure(username); flash('Invalid username or password.','error')
    conn.close(); return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login') if authentication_enabled() else url_for('dashboard'))

@app.route('/')
@login_required
def dashboard():
    refresh_fx_rate()
    conn=db(); accounts=conn.execute('SELECT * FROM accounts WHERE active=1 ORDER BY account_type,name').fetchall(); fx=latest_fx(conn)
    rows=[]
    totals={'gbp':0.0,'eur':0.0}; liquid={'gbp':0.0,'eur':0.0}; pensions={'gbp':0.0,'eur':0.0}; liabilities={'gbp':0.0,'eur':0.0}; other_assets={'gbp':0.0,'eur':0.0}
    liquid_types={'current','savings','premium_bonds','cash'}
    for a in accounts:
        bal=account_balance(conn,a); gbp,eur=dual_values(bal,a['currency'],fx)
        sign=-1 if a['account_type']=='liability' else 1
        totals['gbp'] += sign*gbp; totals['eur'] += sign*eur
        if a['account_type'] in liquid_types:
            liquid['gbp'] += gbp; liquid['eur'] += eur
        elif a['account_type']=='pension':
            pensions['gbp'] += gbp; pensions['eur'] += eur
        elif a['account_type']=='liability':
            liabilities['gbp'] += gbp; liabilities['eur'] += eur
        else:
            # Anything not liquid/pension/liability (e.g. 'other_asset') still
            # counts toward net worth above, but needs its own bucket so the
            # breakdown cards reconcile with the Net Worth total.
            other_assets['gbp'] += gbp; other_assets['eur'] += eur
        rows.append(dict(a, balance=bal, value_gbp=gbp, value_eur=eur))
    recent=conn.execute('''SELECT t.*,a.name account_name,a.currency,c.name category_name,p.name parent_category_name,u.name user_name
                           FROM transactions t JOIN accounts a ON a.id=t.account_id
                           LEFT JOIN categories c ON c.id=t.category_id LEFT JOIN categories p ON p.id=c.parent_id LEFT JOIN users u ON u.id=t.created_by
                           ORDER BY tx_date DESC,t.id DESC LIMIT 12''').fetchall()
    selected_native=[]
    for setting_key in ('dashboard_account_1_id','dashboard_account_2_id'):
        selected_id=get_setting(setting_key,'')
        match=next((x for x in rows if str(x['id'])==str(selected_id)),None) if selected_id else None
        if match: selected_native.append(match)
    conn.close()
    return render_template('dashboard.html',accounts=rows,total=totals,liquid=liquid,pensions=pensions,liabilities=liabilities,other_assets=other_assets,fx=fx,recent=recent,selected_native=selected_native)

@app.route('/accounts', methods=['GET','POST'])
@login_required
def accounts():
    conn=db()
    if request.method=='POST':
        try:
            opening_balance=float(request.form.get('opening_balance') or 0)
        except ValueError:
            opening_balance=None
        if opening_balance is None:
            flash('Enter a valid opening balance.','error')
        else:
            try:
                conn.execute('INSERT INTO accounts(name,account_type,currency,opening_balance,institution,notes) VALUES (?,?,?,?,?,?)',(
                    request.form['name'].strip(),request.form['account_type'],request.form['currency'],opening_balance,request.form.get('institution','').strip(),request.form.get('notes','').strip()))
                conn.commit(); flash('Account added.','ok')
            except sqlite3.IntegrityError:
                flash('Choose a valid currency for the account.','error')
    items=conn.execute('SELECT * FROM accounts ORDER BY active DESC,account_type,name').fetchall(); fx=latest_fx(conn); base=get_setting('base_currency','GBP')
    data=[]
    for a in items:
        bal=account_balance(conn,a); data.append(dict(a,balance=bal,base_value=convert(bal,a['currency'],base,fx)))
    conn.close(); return render_template('accounts.html',accounts=data,base=base)

@app.route('/account/<int:account_id>')
@login_required
def account_detail(account_id):
    conn=db(); a=conn.execute('SELECT * FROM accounts WHERE id=?',(account_id,)).fetchone()
    if not a: abort(404)
    tx=conn.execute('''SELECT t.*,c.name category_name,p.name parent_category_name,u.name user_name FROM transactions t
                       LEFT JOIN categories c ON c.id=t.category_id LEFT JOIN categories p ON p.id=c.parent_id LEFT JOIN users u ON u.id=t.created_by
                       WHERE account_id=? ORDER BY tx_date DESC,id DESC''',(account_id,)).fetchall()
    vals=conn.execute('SELECT * FROM valuations WHERE account_id=? ORDER BY valuation_date DESC,id DESC',(account_id,)).fetchall()
    bal=account_balance(conn,a); conn.close(); return render_template('account_detail.html',a=a,transactions=tx,valuations=vals,balance=bal)

@app.route('/account/<int:account_id>/edit', methods=['GET','POST'])
@login_required
def edit_account(account_id):
    conn=db(); a=conn.execute('SELECT * FROM accounts WHERE id=?',(account_id,)).fetchone()
    if not a:
        conn.close(); abort(404)
    if request.method=='POST':
        name=request.form['name'].strip()
        account_type=request.form['account_type']
        currency=request.form['currency']
        if currency not in ('GBP','EUR'):
            conn.close(); flash('Choose a valid currency for the account.','error'); return redirect(url_for('edit_account',account_id=account_id))
        try:
            opening_balance=float(request.form.get('opening_balance') or 0)
        except ValueError:
            opening_balance=float(a['opening_balance']); flash('Opening balance was not changed because the value was invalid.','error')
        try:
            conn.execute('''UPDATE accounts SET name=?,account_type=?,currency=?,opening_balance=?,institution=?,notes=?,active=? WHERE id=?''',(
                name,account_type,currency,opening_balance,request.form.get('institution','').strip(),request.form.get('notes','').strip(),1 if request.form.get('active')=='1' else 0,account_id))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback(); conn.close(); flash('The account details were not valid. No changes were saved.','error'); return redirect(url_for('edit_account',account_id=account_id))
        conn.close(); flash('Account updated.','ok'); return redirect(url_for('account_detail',account_id=account_id))
    conn.close(); return render_template('account_edit.html',a=a)


@app.route('/transactions', methods=['GET','POST'])
@login_required
def transactions():
    conn=db(); user=current_user()
    if request.method=='POST':
        category_id=int(request.form['category_id']) if request.form.get('category_id') else None
        try:
            account_id=int(request.form['account_id']); amount=float(request.form['amount'])
        except (ValueError,TypeError,KeyError):
            flash('Enter a valid account and amount.','error'); conn.close(); return redirect(url_for('transactions'))
        if not conn.execute("SELECT id FROM accounts WHERE id=? AND active=1 AND account_type NOT IN ('pension','other_asset','liability')",(account_id,)).fetchone():
            flash('Choose a valid active account.','error'); conn.close(); return redirect(url_for('transactions'))
        if amount==0:
            flash('Transaction amount cannot be zero.','error'); conn.close(); return redirect(url_for('transactions'))
        description=request.form.get('description','').strip()
        if not description:
            flash('Description is required.','error'); conn.close(); return redirect(url_for('transactions'))
        # Normalise the sign from the selected category so users can enter a natural positive amount.
        # Transfers are created by the dedicated transfer screen and uncategorised entries retain
        # the sign entered by the user.
        if category_id is not None:
            category=conn.execute('SELECT kind FROM categories WHERE id=?',(category_id,)).fetchone()
            if category:
                if category['kind']=='expense':
                    amount=-abs(amount)
                elif category['kind']=='income':
                    amount=abs(amount)
        conn.execute('''INSERT INTO transactions(account_id,tx_date,description,amount,category_id,tag_text,notes,created_by)
                        VALUES (?,?,?,?,?,?,?,?)''',(
            account_id,safe_date(request.form.get('tx_date'),date.today().isoformat()),description,amount,
            category_id,request.form.get('tags','').strip(),request.form.get('notes','').strip(),user['id']))
        conn.commit(); flash('Transaction added.','ok')
    accts=conn.execute("SELECT * FROM accounts WHERE active=1 AND account_type NOT IN ('pension','other_asset','liability') ORDER BY name").fetchall()
    cats=category_options(conn)
    tx=conn.execute('''SELECT t.*,a.name account_name,a.currency,c.name category_name,p.name parent_category_name,u.name user_name FROM transactions t
                       JOIN accounts a ON a.id=t.account_id LEFT JOIN categories c ON c.id=t.category_id LEFT JOIN categories p ON p.id=c.parent_id LEFT JOIN users u ON u.id=t.created_by
                       ORDER BY tx_date DESC,t.id DESC LIMIT 100''').fetchall(); conn.close()
    return render_template('transactions.html',accounts=accts,categories=cats,transactions=tx,today=date.today().isoformat())

@app.route('/transaction/<int:txid>/category', methods=['POST'])
@login_required
def recategorise_transaction(txid):
    new_id=int(request.form['category_id']) if request.form.get('category_id') else None
    conn=db()
    existing=conn.execute('SELECT transfer_group,amount FROM transactions WHERE id=?',(txid,)).fetchone()
    if not existing: conn.close(); abort(404)
    if existing['transfer_group']:
        conn.close(); flash('Linked transfer entries cannot be recategorised individually.','error'); return redirect(request.referrer or url_for('transactions'))
    amount=float(existing['amount'])
    if new_id is not None:
        cat=conn.execute('SELECT id,kind FROM categories WHERE id=?',(new_id,)).fetchone()
        if not cat: conn.close(); abort(400)
        if cat['kind']=='expense': amount=-abs(amount)
        elif cat['kind']=='income': amount=abs(amount)
    conn.execute('UPDATE transactions SET category_id=?,amount=? WHERE id=?',(new_id,amount,txid))
    conn.commit(); conn.close(); flash('Transaction category updated.','ok')
    return redirect(request.referrer or url_for('transactions'))


@app.route('/transaction/<int:txid>/edit',methods=['GET','POST'])
@login_required
def edit_transaction(txid):
    conn=db(); t=conn.execute('SELECT * FROM transactions WHERE id=?',(txid,)).fetchone()
    if not t: conn.close(); abort(404)
    if t['transfer_group']:
        conn.close(); flash('Linked transfer entries cannot be edited individually. Delete and recreate the transfer if it must change.','error'); return redirect(request.referrer or url_for('transactions'))
    if request.method=='POST':
        category_id=int(request.form['category_id']) if request.form.get('category_id') else None
        amount=abs(float(request.form['amount']))
        if category_id:
            cat=conn.execute('SELECT kind FROM categories WHERE id=?',(category_id,)).fetchone()
            if not cat: conn.close(); abort(400)
            if cat['kind']=='expense': amount=-amount
            elif cat['kind']=='income': amount=amount
            else: amount=-amount if float(t['amount'])<0 else amount
        else:
            amount=-amount if float(t['amount'])<0 else amount

        old_receipt=t['receipt_path']; replacement_receipt=None; new_receipt=old_receipt
        try:
            upload=request.files.get('receipt')
            if upload and upload.filename:
                replacement_receipt=save_receipt(upload)
                new_receipt=replacement_receipt
            if request.form.get('remove_receipt')=='1':
                if replacement_receipt:
                    rp=os.path.join(RECEIPT_DIR,replacement_receipt)
                    if os.path.isfile(rp): os.remove(rp)
                    replacement_receipt=None
                new_receipt=None
            conn.execute('UPDATE transactions SET tx_date=?,description=?,amount=?,category_id=?,tag_text=?,notes=?,receipt_path=? WHERE id=?',
                         (safe_date(request.form.get('tx_date'),t['tx_date']),request.form.get('description','').strip() or t['description'],
                          amount,category_id,request.form.get('tags','').strip(),request.form.get('notes','').strip(),new_receipt,txid))
            conn.commit()
        except Exception:
            if replacement_receipt:
                rp=os.path.join(RECEIPT_DIR,replacement_receipt)
                if os.path.isfile(rp): os.remove(rp)
            conn.close()
            raise
        if old_receipt and old_receipt!=new_receipt:
            delete_if_unreferenced(conn,RECEIPT_DIR,old_receipt)
        conn.close(); flash('Transaction updated.','ok'); return redirect(url_for('transactions'))
    categories=category_options(conn); conn.close(); return render_template('transaction_edit.html',t=t,categories=categories)


@app.route('/transactions/reclassify', methods=['POST'])
@login_required
def reclassify_transactions():
    old_id=int(request.form['old_category_id']) if request.form.get('old_category_id') else None
    new_id=int(request.form['new_category_id']) if request.form.get('new_category_id') else None
    if old_id is None or new_id is None or old_id==new_id:
        flash('Choose two different categories.','error'); return redirect(url_for('categories'))
    conn=db(); old_cat=conn.execute('SELECT * FROM categories WHERE id=?',(old_id,)).fetchone(); new_cat=conn.execute('SELECT * FROM categories WHERE id=?',(new_id,)).fetchone()
    if not old_cat or not new_cat:
        conn.close(); abort(400)
    rows=conn.execute('SELECT id,amount,transfer_group FROM transactions WHERE category_id=?',(old_id,)).fetchall()
    count=0
    for row in rows:
        if row['transfer_group']: continue
        amount=float(row['amount'])
        if new_cat['kind']=='expense': amount=-abs(amount)
        elif new_cat['kind']=='income': amount=abs(amount)
        conn.execute('UPDATE transactions SET category_id=?,amount=? WHERE id=?',(new_id,amount,row['id'])); count+=1
    pending=conn.execute('SELECT id,amount FROM pending_transactions WHERE category_id=?',(old_id,)).fetchall()
    for row in pending:
        amount=float(row['amount']); entry_type='expense' if amount<0 else 'income'
        if new_cat['kind']=='expense': amount=-abs(amount); entry_type='expense'
        elif new_cat['kind']=='income': amount=abs(amount); entry_type='income'
        conn.execute('UPDATE pending_transactions SET category_id=?,amount=?,entry_type=? WHERE id=?',(new_id,amount,entry_type,row['id']))
    conn.commit(); conn.close()
    flash(f'Re-categorised {count} existing transaction(s). Linked transfers were left unchanged.','ok')
    return redirect(url_for('categories'))


@app.route('/transaction/<int:txid>/delete', methods=['POST'])
@login_required
def delete_transaction(txid):
    conn=db(); row=conn.execute('SELECT id,transfer_group,receipt_path FROM transactions WHERE id=?',(txid,)).fetchone()
    if not row: conn.close(); abort(404)
    receipts=[]
    if row['transfer_group']:
        pair=conn.execute('SELECT receipt_path FROM transactions WHERE transfer_group=?',(row['transfer_group'],)).fetchall(); receipts=[r['receipt_path'] for r in pair if r['receipt_path']]; conn.execute('DELETE FROM transactions WHERE transfer_group=?',(row['transfer_group'],)); message='Transfer and both linked account entries deleted.'
    else:
        if row['receipt_path']: receipts=[row['receipt_path']]
        conn.execute('DELETE FROM transactions WHERE id=?',(txid,)); message='Transaction deleted.'
    conn.commit()
    for filename in set(receipts): delete_if_unreferenced(conn,RECEIPT_DIR,filename)
    conn.close(); flash(message,'ok'); return redirect(request.referrer or url_for('transactions'))

@app.route('/transfer', methods=['GET','POST'])
@login_required
def transfer():
    conn=db(); user=current_user()
    if request.method=='POST':
        try:
            from_id=int(request.form['from_account']); to_id=int(request.form['to_account'])
            out_amt=abs(float(request.form['from_amount'])); in_amt=abs(float(request.form['to_amount']))
        except (ValueError,TypeError,KeyError):
            from_id=to_id=None; out_amt=in_amt=0
            flash('Enter valid transfer accounts and amounts.','error')
        fa=conn.execute('SELECT * FROM accounts WHERE id=?',(from_id,)).fetchone() if from_id else None
        ta=conn.execute('SELECT * FROM accounts WHERE id=?',(to_id,)).fetchone() if to_id else None
        if not fa or not ta or from_id==to_id:
            flash('Choose two different valid accounts.','error')
        elif out_amt<=0 or in_amt<=0:
            flash('Transfer amounts must be greater than zero.','error')
        else:
            group=secrets.token_hex(8); d=safe_date(request.form.get('tx_date'),date.today().isoformat()); desc=request.form.get('description','Transfer').strip() or 'Transfer'
            cat=conn.execute("SELECT id FROM categories WHERE name='Transfer'").fetchone()
            cid=cat['id'] if cat else None
            conn.execute('INSERT INTO transactions(account_id,tx_date,description,amount,category_id,tag_text,notes,transfer_group,created_by) VALUES (?,?,?,?,?,?,?,?,?)',(from_id,d,desc,-out_amt,cid,'Transfer',f'Transfer to {ta["name"]}',group,user['id']))
            conn.execute('INSERT INTO transactions(account_id,tx_date,description,amount,category_id,tag_text,notes,transfer_group,created_by) VALUES (?,?,?,?,?,?,?,?,?)',(to_id,d,desc,in_amt,cid,'Transfer',f'Transfer from {fa["name"]}',group,user['id']))
            conn.commit(); flash('Transfer recorded.','ok'); conn.close(); return redirect(url_for('transactions'))
    accts=conn.execute("SELECT * FROM accounts WHERE active=1 AND account_type NOT IN ('pension','other_asset','liability') ORDER BY name").fetchall(); conn.close()
    return render_template('transfer.html',accounts=accts,today=date.today().isoformat())

@app.route('/valuations', methods=['GET','POST'])
@login_required
def valuations():
    conn=db(); user=current_user()
    if request.method=='POST':
        try:
            account_id=int(request.form['account_id']); value=float(request.form['value'])
        except (ValueError,TypeError,KeyError):
            flash('Choose a valid account and valuation amount.','error')
        else:
            valid=conn.execute("SELECT id FROM accounts WHERE id=? AND active=1 AND account_type IN ('pension','other_asset','liability')",(account_id,)).fetchone()
            if not valid:
                flash('Choose a valid valuation account.','error')
            else:
                conn.execute('''INSERT INTO valuations(account_id,valuation_date,value,notes,created_by) VALUES (?,?,?,?,?)
                                ON CONFLICT(account_id,valuation_date) DO UPDATE SET value=excluded.value,notes=excluded.notes,created_by=excluded.created_by''',
                             (account_id,safe_date(request.form.get('valuation_date'),date.today().isoformat()),value,request.form.get('notes','').strip(),user['id']))
                conn.commit(); flash('Valuation saved.','ok')
    accts=conn.execute("SELECT * FROM accounts WHERE active=1 AND account_type IN ('pension','other_asset','liability') ORDER BY name").fetchall()
    vals=conn.execute('''SELECT v.*,a.name account_name,a.currency,a.account_type,u.name user_name FROM valuations v JOIN accounts a ON a.id=v.account_id LEFT JOIN users u ON u.id=v.created_by ORDER BY valuation_date DESC,v.id DESC LIMIT 100''').fetchall(); conn.close()
    return render_template('valuations.html',accounts=accts,valuations=vals,today=date.today().isoformat())

def save_category_parent(conn, category_id, parent_id):
    return category_save_parent(conn, category_id, parent_id)


@app.route('/categories', methods=['GET','POST'])
@login_required
def categories():
    conn=db()
    if request.method=='POST':
        action=request.form.get('action','add')
        if action=='add':
            name=request.form['name'].strip(); kind=request.form['kind']; parent_id=int(request.form['parent_id']) if request.form.get('parent_id') else None
            if parent_id:
                parent=conn.execute('SELECT * FROM categories WHERE id=?',(parent_id,)).fetchone()
                if not parent: conn.close(); abort(400)
                kind=parent['kind']
            try:
                conn.execute('INSERT INTO categories(name,kind,parent_id) VALUES (?,?,?)',(name,kind,parent_id)); conn.commit(); flash('Category added.','ok')
            except sqlite3.IntegrityError: flash('That category already exists.','error')
        elif action=='rename':
            cid=int(request.form['category_id']); name=request.form['name'].strip()
            try:
                conn.execute('UPDATE categories SET name=? WHERE id=?',(name,cid)); conn.commit(); flash('Category renamed.','ok')
            except sqlite3.IntegrityError: flash('That category name already exists.','error')
        elif action=='set_parent':
            cid=int(request.form['category_id'])
            parent_id=request.form.get('parent_id') or None
            ok,message=save_category_parent(conn,cid,parent_id)
            flash(message,'ok' if ok else 'error')
        elif action=='delete':
            cid=int(request.form['category_id']); replacement=request.form.get('replacement_id','').strip()
            cat=conn.execute('SELECT * FROM categories WHERE id=?',(cid,)).fetchone()
            if not cat:
                conn.close(); abort(404)
            child_count=conn.execute('SELECT COUNT(*) n FROM categories WHERE parent_id=?',(cid,)).fetchone()['n']
            tx_count=conn.execute('SELECT COUNT(*) n FROM transactions WHERE category_id=?',(cid,)).fetchone()['n']
            pending_count=conn.execute('SELECT COUNT(*) n FROM pending_transactions WHERE category_id=?',(cid,)).fetchone()['n']
            if child_count:
                flash('Move, reassign or delete this category’s subcategories before deleting the parent category.','error')
            elif tx_count or pending_count:
                if not replacement:
                    flash(f'This category is in use by {tx_count} transaction(s) and {pending_count} pending item(s). Choose a replacement category first.','error')
                else:
                    rid=int(replacement); repl=conn.execute('SELECT * FROM categories WHERE id=?',(rid,)).fetchone()
                    if not repl or rid==cid:
                        flash('Choose a valid replacement category.','error')
                    elif repl['kind'] != cat['kind']:
                        flash('The replacement category must be the same type.','error')
                    else:
                        conn.execute('UPDATE transactions SET category_id=? WHERE category_id=?',(rid,cid))
                        conn.execute('UPDATE pending_transactions SET category_id=? WHERE category_id=?',(rid,cid))
                        conn.execute('DELETE FROM categories WHERE id=?',(cid,)); conn.commit(); flash('Category deleted and existing items reassigned.','ok')
            else:
                conn.execute('DELETE FROM categories WHERE id=?',(cid,)); conn.commit(); flash('Category deleted.','ok')
    items=category_options(conn); parents=[dict(r,label=r['name']) for r in category_rows(conn) if not r['parent_id']]
    counts={r['category_id']:r['n'] for r in conn.execute('SELECT category_id,COUNT(*) n FROM transactions WHERE category_id IS NOT NULL GROUP BY category_id').fetchall()}
    conn.close(); return render_template('categories.html',categories=items,parents=parents,counts=counts)

@app.route('/reports/categories')
@login_required
def category_report():
    default_start,default_end=month_bounds()
    start=safe_date(request.args.get('start'),default_start); end=safe_date(request.args.get('end'),default_end)
    if start>end: start,end=end,start
    kind=request.args.get('kind','').strip()
    selected_account_ids=sorted({int(x) for x in request.args.getlist('account_id') if x.isdigit()})
    selected_ids=sorted({int(x) for x in request.args.getlist('category_id') if x.isdigit()})
    conn=db(); fx=latest_fx(conn)
    params=[start,end]; where=['t.tx_date BETWEEN ? AND ?']
    if selected_account_ids:
        qs=','.join('?' for _ in selected_account_ids)
        where.append(f't.account_id IN ({qs})'); params.extend(selected_account_ids)
    if kind in ('income','expense','transfer','other'): where.append('c.kind=?'); params.append(kind)
    if selected_ids:
        qs=','.join('?' for _ in selected_ids)
        where.append(f'(c.id IN ({qs}) OR p.id IN ({qs}))'); params.extend(selected_ids); params.extend(selected_ids)
    sql=f"""SELECT t.*,a.name account_name,a.currency,c.id category_id,c.name category_name,c.kind category_kind,
                   p.id parent_id,p.name parent_name
            FROM transactions t JOIN accounts a ON a.id=t.account_id
            LEFT JOIN categories c ON c.id=t.category_id LEFT JOIN categories p ON p.id=c.parent_id
            WHERE {' AND '.join(where)} ORDER BY c.kind,COALESCE(p.name,c.name),c.name,t.tx_date,t.id"""
    tx=conn.execute(sql,params).fetchall(); parents={}
    for t in tx:
        ckind=t['category_kind'] or 'other'; parent_name=t['parent_name'] or t['category_name'] or 'Uncategorised'; sub_name=t['category_name'] if t['parent_name'] else None
        pk=(ckind,parent_name); pg=parents.setdefault(pk,{'kind':ckind,'name':parent_name,'gbp':0.0,'eur':0.0,'count':0,'transactions':[],'subcategories':{},'role':'category'})
        if t['parent_name']:
            pg['role']='parent'
        gbp,eur=display_report_values(t['amount'],t['currency'],fx,ckind,dual_values)
        pg['gbp']+=gbp; pg['eur']+=eur; pg['count']+=1; pg['transactions'].append(t)
        if sub_name:
            sg=pg['subcategories'].setdefault(sub_name,{'name':sub_name,'gbp':0.0,'eur':0.0,'count':0,'transactions':[]}); sg['gbp']+=gbp; sg['eur']+=eur; sg['count']+=1; sg['transactions'].append(t)
    report_rows=[]
    for g in parents.values():
        g['subcategories']=sorted(g['subcategories'].values(),key=lambda x:-abs(x['gbp'])); report_rows.append(g)
    report_rows.sort(key=lambda x:(x['kind'],-abs(x['gbp']),x['name'].lower()))
    totals={'gbp':sum(x['gbp'] for x in report_rows),'eur':sum(x['eur'] for x in report_rows)}
    accounts=conn.execute("SELECT id,name,currency FROM accounts WHERE active=1 AND account_type NOT IN ('pension','other_asset','liability') ORDER BY name").fetchall()
    category_groups=category_selector_groups(conn); conn.close()
    return render_template('category_report.html',rows=report_rows,accounts=accounts,category_groups=category_groups,start=start,end=end,selected_account_ids=selected_account_ids,kind=kind,fx=fx,totals=totals,selected_category_ids=selected_ids)

@app.route('/reports/categories.pdf')
@login_required
def category_report_pdf():
    default_start,default_end=month_bounds(); start=safe_date(request.args.get('start'),default_start); end=safe_date(request.args.get('end'),default_end)
    if start>end: start,end=end,start
    kind=request.args.get('kind','').strip()
    selected_account_ids=sorted({int(x) for x in request.args.getlist('account_id') if x.isdigit()})
    selected_ids=sorted({int(x) for x in request.args.getlist('category_id') if x.isdigit()})
    conn=db(); fx=latest_fx(conn); params=[start,end]; where=['t.tx_date BETWEEN ? AND ?']
    if selected_account_ids:
        qs=','.join('?' for _ in selected_account_ids); where.append(f't.account_id IN ({qs})'); params.extend(selected_account_ids)
    if kind in ('income','expense','transfer','other'): where.append('c.kind=?'); params.append(kind)
    if selected_ids:
        qs=','.join('?' for _ in selected_ids); where.append(f'(c.id IN ({qs}) OR p.id IN ({qs}))'); params.extend(selected_ids); params.extend(selected_ids)
    rows=conn.execute(f"""SELECT c.id category_id,c.name category_name,c.kind category_kind,p.id parent_id,p.name parent_name,a.currency,t.amount
                          FROM transactions t JOIN accounts a ON a.id=t.account_id LEFT JOIN categories c ON c.id=t.category_id LEFT JOIN categories p ON p.id=c.parent_id
                          WHERE {' AND '.join(where)} ORDER BY c.kind,COALESCE(p.name,c.name),c.name""",params).fetchall()
    groups={}; parent_totals={}; total_gbp=total_eur=0.0
    for r in rows:
        parent=r['parent_name'] or r['category_name'] or 'Uncategorised'; sub=r['category_name'] if r['parent_name'] else ''; kind2=r['category_kind'] or 'other'
        key=(kind2,parent,sub); g=groups.setdefault(key,[0.0,0.0,0]); gbp,eur=display_report_values(r['amount'],r['currency'],fx,kind2,dual_values)
        g[0]+=gbp; g[1]+=eur; g[2]+=1
        pg=parent_totals.setdefault((kind2,parent),[0.0,0.0,0]); pg[0]+=gbp; pg[1]+=eur; pg[2]+=1; total_gbp+=gbp; total_eur+=eur
    data=[['Category','Subcategory','Type','Transactions','GBP','EUR']]
    for (kind2,parent),(gbp,eur,count) in sorted(parent_totals.items(),key=lambda x:(x[0][0],-abs(x[1][0]),x[0][1].lower())):
        data.append([parent,'',kind2.title(),str(count),f'£{gbp:,.2f}',f'€{eur:,.2f}'])
        for (k,pname,sub),(sgbp,seur,scount) in sorted(groups.items()):
            if k==kind2 and pname==parent and sub: data.append(['',sub,'',str(scount),f'£{sgbp:,.2f}',f'€{seur:,.2f}'])
    data.append(['TOTAL','','','',f'£{total_gbp:,.2f}',f'€{total_eur:,.2f}']); conn.close()
    selection='Selected categories' if selected_ids else 'All categories'
    account_selection=f'{len(selected_account_ids)} selected account(s)' if selected_account_ids else 'All accounts'
    buf=io.BytesIO(); doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=10*mm,leftMargin=10*mm,topMargin=15*mm,bottomMargin=15*mm); styles=getSampleStyleSheet()
    story=[Paragraph(get_setting('household_name','Household Finance'),styles['Title']),Paragraph('Category & Subcategory Report',styles['Heading2']),Paragraph(f'Period: {start} to {end} | {account_selection} | {selection} | Type: {kind.title() if kind else "All"} | GBP/EUR rate: {fx:.4f}',styles['Normal']),Spacer(1,6*mm)]
    table=Table(data,colWidths=[42*mm,42*mm,24*mm,22*mm,28*mm,28*mm],repeatRows=1); table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.lightgrey),('GRID',(0,0),(-1,-1),0.25,colors.grey),('ALIGN',(3,1),(-1,-1),'RIGHT'),('FONTSIZE',(0,0),(-1,-1),7.5),('FONTNAME',(0,-1),(-1,-1),'Helvetica-Bold')]))
    story.append(table); doc.build(story); buf.seek(0); return send_file(buf,mimetype='application/pdf',as_attachment=request.args.get('share')!='1',download_name=f'category_report_{start}_to_{end}.pdf')

@app.route('/system')
@admin_required
def system_status():
    return render_template('system.html',tailscale=tailscale_status(),local_url='http://127.0.0.1:8080')

@app.route('/settings', methods=['GET','POST'])
@admin_required
def settings():
    conn=db()
    if request.method=='POST':
        set_setting('base_currency',request.form['base_currency'])
        set_setting('household_name',request.form['household_name'].strip() or 'Household Finance')
        set_setting('fx_auto','1' if request.form.get('fx_auto')=='1' else '0')
        requested_auth='1' if request.form.get('auth_required')=='1' else '0'
        requested_tailnet='1' if request.form.get('tailnet_only')=='1' else '0'
        if requested_auth=='1':
            active_admins=conn.execute("SELECT COUNT(*) n FROM users WHERE role='admin' AND COALESCE(active,1)=1").fetchone()['n']
            if active_admins==0:
                flash('Create or reactivate at least one Administrator before enabling credentials.','error')
                requested_auth='0'
        set_setting('auth_required',requested_auth); set_setting('tailnet_only',requested_tailnet)
        for key in ('dashboard_account_1_id','dashboard_account_2_id'):
            aid=request.form.get(key,'').strip(); valid=conn.execute('SELECT id FROM accounts WHERE id=? AND active=1',(aid,)).fetchone() if aid else None; set_setting(key,aid if valid else '')
        set_setting('backup_enabled','1' if request.form.get('backup_enabled')=='1' else '0')
        set_setting('backup_location',request.form.get('backup_location','').strip())
        freq=request.form.get('backup_frequency','daily'); set_setting('backup_frequency',freq if freq in ('daily','weekly','monthly') else 'daily')
        retention=request.form.get('backup_retention','10').strip(); set_setting('backup_retention',retention if retention.isdigit() and int(retention)>0 else '10')
        set_setting('dropbox_enabled','1' if request.form.get('dropbox_enabled')=='1' else '0')
        set_setting('dropbox_folder',request.form.get('dropbox_folder','FinanceTracker').strip() or 'FinanceTracker')
        token=request.form.get('dropbox_token','').strip()
        if token:
            try: set_dropbox_token(token)
            except RuntimeError as exc: flash(str(exc),'error')
        set_setting('licensed_to',request.form.get('licensed_to','').strip()); set_setting('licence_number',request.form.get('licence_number','').strip())
        quick_id=request.form.get('quick_account_id','').strip()
        if quick_id:
            valid=conn.execute("SELECT id FROM accounts WHERE id=? AND active=1 AND account_type NOT IN ('pension','other_asset','liability')",(quick_id,)).fetchone()
            set_setting('quick_account_id',quick_id if valid else '')
        else:
            set_setting('quick_account_id','')
        if request.form.get('gbp_to_eur'):
            try:
                conn.execute('''INSERT INTO fx_rates(rate_date,gbp_to_eur,source) VALUES (?,?,?)
                                ON CONFLICT(rate_date) DO UPDATE SET gbp_to_eur=excluded.gbp_to_eur,source=excluded.source''',
                             (request.form['rate_date'],float(request.form['gbp_to_eur']),'Manual'))
                conn.commit()
            except ValueError: flash('Invalid exchange rate.','error')
        flash('Settings saved.','ok')
    if get_setting('fx_auto','1')=='1': refresh_fx_rate()
    rate=latest_fx(conn)
    history=conn.execute('SELECT * FROM fx_rates ORDER BY rate_date DESC LIMIT 20').fetchall()
    quick_accounts=conn.execute("SELECT id,name,currency FROM accounts WHERE active=1 AND account_type NOT IN ('pension','other_asset','liability') ORDER BY name").fetchall()
    dashboard_accounts=conn.execute('SELECT id,name,currency FROM accounts WHERE active=1 ORDER BY name').fetchall(); ts=tailscale_status()
    security_status={'tailnet_only':tailnet_only_enabled(),'credentials':authentication_enabled(),'tailscale':ts,'https':bool(ts.get('url','').startswith('https://')),'exposure':'Tailnet only' if tailnet_only_enabled() else 'Direct LAN access permitted'}
    conn.close()
    return render_template('settings.html',base=get_setting('base_currency','GBP'),household=get_setting('household_name','Household Finance'),rate=rate,history=history,today=date.today().isoformat(),fx_auto=get_setting('fx_auto','1'),fx_status=get_setting('fx_last_status','Not checked yet'),quick_account_id=get_setting('quick_account_id',''),quick_accounts=quick_accounts,auth_required=get_setting('auth_required','0'),tailnet_only=get_setting('tailnet_only','1'),security_status=security_status,dashboard_accounts=dashboard_accounts,dashboard_account_1_id=get_setting('dashboard_account_1_id',''),dashboard_account_2_id=get_setting('dashboard_account_2_id',''),backup_enabled=get_setting('backup_enabled','1'),backup_location=get_setting('backup_location',''),backup_frequency=get_setting('backup_frequency','daily'),backup_retention=get_setting('backup_retention','10'),backup_last_status=get_setting('backup_last_status','Never'),dropbox_enabled=get_setting('dropbox_enabled','0'),dropbox_folder=get_setting('dropbox_folder','FinanceTracker'),dropbox_token_configured=bool(get_dropbox_token()),dropbox_last_status=get_setting('dropbox_last_status','Not tested'),dropbox_last_success_date=get_setting('dropbox_last_success_date',''),dropbox_retry_count=get_setting('dropbox_retry_count','0'),dropbox_next_retry=get_setting('dropbox_next_retry',''),licensed_to=get_setting('licensed_to',''),licence_number=get_setting('licence_number',''))

@app.route('/settings/backup-now',methods=['POST'])
@admin_required
def settings_backup_now():
    ok,msg,path=create_local_backup(); flash(msg,'ok' if ok else 'error'); return redirect(url_for('settings'))

@app.route('/settings/dropbox-test',methods=['POST'])
@admin_required
def settings_dropbox_test():
    ok,msg=test_dropbox_connection(); flash(msg,'ok' if ok else 'error'); return redirect(url_for('settings'))

@app.route('/settings/dropbox-backup',methods=['POST'])
@admin_required
def settings_dropbox_backup():
    if get_setting('dropbox_enabled','0')!='1': flash('Enable Dropbox backup in Settings first.','error'); return redirect(url_for('settings'))
    ok,msg=create_dropbox_backup(); flash(msg,'ok' if ok else 'error'); return redirect(url_for('settings'))

@app.route('/settings/refresh-fx', methods=['POST'])
@admin_required
def refresh_fx():
    ok,msg=refresh_fx_rate(force=True)
    flash(msg,'ok' if ok else 'error')
    return redirect(url_for('settings'))

@app.route('/quick', methods=['GET','POST'])
@login_required
def quick_entry():
    conn=db(); user=current_user()
    accounts=conn.execute("SELECT id,name,currency FROM accounts WHERE active=1 AND account_type NOT IN ('pension','other_asset','liability') ORDER BY name").fetchall()
    categories=category_options(conn,('expense','income','other'))
    quick_id=get_setting('quick_account_id','')
    if not quick_id and accounts: quick_id=str(accounts[0]['id'])
    values={'tx_date':date.today().isoformat(),'description':'','amount':'','category_id':'','entry_type':'expense','notes':'','receipt_path':'','ocr_text':''}
    if request.method=='POST':
        action=request.form.get('action','save')
        values={k:request.form.get(k,'') for k in values}
        values['receipt_path']=session.get('quick_receipt_path','')
        try:
            uploaded=request.files.get('receipt')
            if uploaded and uploaded.filename:
                old=session.get('quick_receipt_path','')
                new_receipt_path=save_receipt(uploaded) or ''
                session['quick_receipt_path']=new_receipt_path
                values['receipt_path']=new_receipt_path
                if old and old!=new_receipt_path:
                    old_path=os.path.join(RECEIPT_DIR,old)
                    if os.path.isfile(old_path): os.remove(old_path)
            if action=='scan':
                if not values.get('receipt_path'):
                    flash('Choose a receipt image first.','error')
                else:
                    text=ocr_receipt(values['receipt_path'])
                    values['ocr_text']=text
                    parsed=parse_receipt_text(conn,text)
                    values.update({k:str(v) if v is not None else '' for k,v in parsed.items()})
                    flash('Receipt scanned. Check the details, then tap Save pending.','ok')
            else:
                account_id=int(request.form.get('account_id') or quick_id)
                account=conn.execute("SELECT * FROM accounts WHERE id=? AND active=1 AND account_type NOT IN ('pension','other_asset','liability')",(account_id,)).fetchone()
                if not account: raise ValueError('Choose a valid account.')
                description=values['description'].strip()
                if not description: raise ValueError('Description is required.')
                amount=abs(float(values['amount']))
                if amount<=0: raise ValueError('Amount must be greater than zero.')
                category_id=int(values['category_id']) if values.get('category_id') else None
                entry_type=values.get('entry_type','expense') if values.get('entry_type') in ('expense','income') else 'expense'
                if category_id:
                    cat=conn.execute('SELECT kind FROM categories WHERE id=?',(category_id,)).fetchone()
                    if cat and cat['kind'] in ('expense','income'): entry_type=cat['kind']
                amount=-amount if entry_type=='expense' else amount
                conn.execute('''INSERT INTO pending_transactions(account_id,tx_date,description,amount,category_id,entry_type,notes,receipt_path,ocr_text,created_by)
                                VALUES (?,?,?,?,?,?,?,?,?,?)''',(account_id,safe_date(values['tx_date'],date.today().isoformat()),description,amount,category_id,entry_type,values['notes'].strip(),values.get('receipt_path') or None,values.get('ocr_text') or None,user['id']))
                conn.commit(); session.pop('quick_receipt_path',None); flash('Quick entry saved as pending.','ok'); conn.close(); return redirect(url_for('quick_entry'))
        except (ValueError,RuntimeError) as exc:
            flash(str(exc),'error')
    pending_count=conn.execute('SELECT COUNT(*) n FROM pending_transactions').fetchone()['n']
    conn.close()
    return render_template('quick_entry.html',accounts=accounts,categories=categories,quick_account_id=quick_id,values=values,pending_count=pending_count)

@app.route('/pending')
@login_required
def pending_entries():
    conn=db()
    rows=conn.execute('''SELECT p.*,a.name account_name,a.currency,c.name category_name
                         FROM pending_transactions p JOIN accounts a ON a.id=p.account_id
                         LEFT JOIN categories c ON c.id=p.category_id ORDER BY p.tx_date DESC,p.id DESC''').fetchall()
    cats=category_options(conn,('expense','income','other'))
    conn.close(); return render_template('pending.html',rows=rows,categories=cats)

@app.route('/pending/<int:pid>/post', methods=['POST'])
@login_required
def post_pending(pid):
    conn=db(); user=current_user(); p=conn.execute('SELECT * FROM pending_transactions WHERE id=?',(pid,)).fetchone()
    if not p: conn.close(); abort(404)
    try:
        category_id=int(request.form['category_id']) if request.form.get('category_id') else None
        amount=abs(float(request.form['amount']))
    except (ValueError,TypeError,KeyError):
        conn.close(); flash('Enter a valid amount and category.','error'); return redirect(url_for('pending_entries'))
    if amount<=0:
        conn.close(); flash('Amount must be greater than zero.','error'); return redirect(url_for('pending_entries'))
    entry_type=request.form.get('entry_type') or p['entry_type'] or ('expense' if float(p['amount'])<0 else 'income')
    if entry_type not in ('expense','income'): entry_type='expense'
    if category_id:
        cat=conn.execute('SELECT kind FROM categories WHERE id=?',(category_id,)).fetchone()
        if cat and cat['kind'] in ('expense','income'): entry_type=cat['kind']
    amount=-amount if entry_type=='expense' else amount
    conn.execute('''INSERT INTO transactions(account_id,tx_date,description,amount,category_id,tag_text,notes,receipt_path,created_by)
                    VALUES (?,?,?,?,?,?,?,?,?)''',(p['account_id'],safe_date(request.form.get('tx_date'),p['tx_date']),request.form.get('description','').strip() or p['description'],amount,category_id,'Quick Entry',request.form.get('notes','').strip(),p['receipt_path'],user['id']))
    conn.execute('DELETE FROM pending_transactions WHERE id=?',(pid,)); conn.commit(); conn.close(); flash('Pending entry posted to the account.','ok')
    return redirect(url_for('pending_entries'))

@app.route('/pending/<int:pid>/delete', methods=['POST'])
@login_required
def delete_pending(pid):
    conn=db(); p=conn.execute('SELECT receipt_path FROM pending_transactions WHERE id=?',(pid,)).fetchone()
    if p:
        conn.execute('DELETE FROM pending_transactions WHERE id=?',(pid,)); conn.commit()
        if p['receipt_path']:
            delete_if_unreferenced(conn,RECEIPT_DIR,p['receipt_path'])
    conn.close(); flash('Pending entry deleted.','ok'); return redirect(url_for('pending_entries'))

@app.route('/receipt/<path:filename>')
@login_required
def receipt_file(filename):
    if os.path.basename(filename)!=filename: abort(404)
    return send_from_directory(RECEIPT_DIR,filename)

@app.route('/users', methods=['GET','POST'])
@admin_required
def users():
    conn=db()
    def active_admin_count():
        return conn.execute("SELECT COUNT(*) n FROM users WHERE role='admin' AND COALESCE(active,1)=1").fetchone()['n']
    if request.method=='POST':
        action=request.form.get('action','add')
        if action=='add':
            pw=request.form.get('password','')
            if len(pw)<10: flash('Password must be at least 10 characters.','error')
            else:
                try:
                    conn.execute('INSERT INTO users(name,username,password_hash,role,active,auth_version) VALUES (?,?,?,?,1,1)',
                                 (request.form['name'].strip(),request.form['username'].strip().lower(),generate_password_hash(pw),request.form['role']))
                    conn.commit(); flash('User added.','ok')
                except sqlite3.IntegrityError: flash('Username already exists.','error')
        else:
            uid=int(request.form['user_id']); u=conn.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
            if not u: conn.close(); abort(404)
            if action=='update':
                name=request.form.get('name','').strip() or u['name']; username=request.form.get('username','').strip().lower() or u['username']
                role=request.form.get('role','member'); active=1 if request.form.get('active')=='1' else 0
                last_admin=(u['role']=='admin' and u['active'] and (role!='admin' or not active) and active_admin_count()<=1)
                if last_admin: flash('Finance Tracker must retain at least one active Administrator.','error')
                elif u['id']==session.get('user_id') and not active: flash('You cannot disable the account you are currently signed in with.','error')
                else:
                    try:
                        conn.execute('UPDATE users SET name=?,username=?,role=?,active=?,auth_version=auth_version+1 WHERE id=?',(name,username,role,active,uid)); conn.commit()
                        if uid==session.get('user_id'):
                            session['auth_version']=conn.execute('SELECT auth_version FROM users WHERE id=?',(uid,)).fetchone()['auth_version']
                        flash('User updated.','ok')
                    except sqlite3.IntegrityError: flash('Username already exists.','error')
            elif action=='reset_password':
                pw=request.form.get('password','')
                if len(pw)<10: flash('Password must be at least 10 characters.','error')
                else:
                    conn.execute('UPDATE users SET password_hash=?,auth_version=auth_version+1 WHERE id=?',(generate_password_hash(pw),uid)); conn.commit()
                    if uid==session.get('user_id'):
                        session.clear(); flash('Password reset. Please sign in again.','ok'); conn.close(); return redirect(url_for('login'))
                    flash('Password reset. Existing sessions for that user have been invalidated.','ok')
            elif action=='delete':
                if u['role']=='admin' and u['active'] and active_admin_count()<=1:
                    flash('The last active Administrator cannot be deleted or disabled.','error')
                elif u['id']==session.get('user_id'):
                    flash('You cannot delete the account you are currently signed in with.','error')
                else:
                    refs=conn.execute('SELECT (SELECT COUNT(*) FROM transactions WHERE created_by=?)+(SELECT COUNT(*) FROM pending_transactions WHERE created_by=?)+(SELECT COUNT(*) FROM valuations WHERE created_by=?) n',(uid,uid,uid)).fetchone()['n']
                    if refs:
                        conn.execute('UPDATE users SET active=0,auth_version=auth_version+1 WHERE id=?',(uid,)); conn.commit(); flash('User has historical audit records and was disabled instead of deleted.','ok')
                    else:
                        conn.execute('DELETE FROM users WHERE id=?',(uid,)); conn.commit(); flash('User deleted.','ok')
    rows=conn.execute('SELECT id,name,username,role,COALESCE(active,1) active,created_at FROM users ORDER BY name').fetchall()
    conn.close(); return render_template('users.html',users=rows)


@app.route('/report/account/<int:account_id>.pdf')
@login_required
def account_pdf(account_id):
    start=safe_date(request.args.get('start'),'0001-01-01'); end=safe_date(request.args.get('end'),'9999-12-31')
    if start>end: start,end=end,start
    conn=db(); a=conn.execute('SELECT * FROM accounts WHERE id=?',(account_id,)).fetchone()
    if not a: abort(404)
    tx=conn.execute('''SELECT t.*,c.name category_name FROM transactions t LEFT JOIN categories c ON c.id=t.category_id WHERE account_id=? AND tx_date BETWEEN ? AND ? ORDER BY tx_date,id''',(account_id,start,end)).fetchall(); conn.close()
    buf=io.BytesIO(); doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=15*mm,leftMargin=15*mm,topMargin=15*mm,bottomMargin=15*mm); styles=getSampleStyleSheet(); story=[]
    story += [Paragraph(get_setting('household_name','Household Finance'),styles['Title']),Paragraph(f'Account Statement — {a["name"]}',styles['Heading2']),Paragraph(f'Period: {start} to {end} | Currency: {a["currency"]}',styles['Normal']),Spacer(1,6*mm)]
    data=[['Date','Description','Category','Tags','Amount']]
    for t in tx: data.append([t['tx_date'],t['description'],t['category_name'] or '',t['tag_text'] or '',f'{t["amount"]:,.2f}'])
    table=Table(data,colWidths=[25*mm,65*mm,38*mm,30*mm,25*mm],repeatRows=1); table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.lightgrey),('GRID',(0,0),(-1,-1),0.25,colors.grey),('ALIGN',(-1,1),(-1,-1),'RIGHT'),('FONTSIZE',(0,0),(-1,-1),8),('VALIGN',(0,0),(-1,-1),'TOP')]))
    story.append(table); doc.build(story); buf.seek(0)
    return send_file(buf,mimetype='application/pdf',as_attachment=request.args.get('share')!='1',download_name=f'{a["name"].replace(" ","_")}_statement.pdf')

@app.route('/report/net-worth.pdf')
@login_required
def networth_pdf():
    conn=db(); accounts=conn.execute('SELECT * FROM accounts WHERE active=1 ORDER BY account_type,name').fetchall(); fx=latest_fx(conn); base=get_setting('base_currency','GBP'); data=[['Account','Type',f'Value ({base})']]; total=0
    for a in accounts:
        bal=account_balance(conn,a); b=convert(bal,a['currency'],base,fx); signed=-b if a['account_type']=='liability' else b; total += signed
        data.append([a['name'],a['account_type'].replace('_',' ').title(),f'{signed:,.2f}'])
    data.append(['','Net Worth',f'{total:,.2f}'])
    conn.close(); buf=io.BytesIO(); doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=15*mm,leftMargin=15*mm,topMargin=15*mm,bottomMargin=15*mm); styles=getSampleStyleSheet(); story=[Paragraph(get_setting('household_name','Household Finance'),styles['Title']),Paragraph(f'Net Worth Statement — {date.today().isoformat()}',styles['Heading2']),Paragraph(f'GBP/EUR rate used: {fx:.4f}',styles['Normal']),Spacer(1,6*mm)]
    table=Table(data,colWidths=[80*mm,50*mm,50*mm],repeatRows=1); table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.lightgrey),('GRID',(0,0),(-1,-1),0.25,colors.grey),('ALIGN',(-1,1),(-1,-1),'RIGHT'),('FONTSIZE',(0,0),(-1,-1),8),('FONTNAME',(0,-1),(-1,-1),'Helvetica-Bold')]))
    story.append(table); doc.build(story); buf.seek(0); return send_file(buf,mimetype='application/pdf',as_attachment=request.args.get('share')!='1',download_name='net_worth_statement.pdf')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT','8080')), debug=False)
