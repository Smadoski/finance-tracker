"""Authenticated configuration and read-only reports for the financial-health model."""
import math
from datetime import date
from flask import Blueprint, request, render_template, redirect, url_for, flash
from .classifications import ASSET_CLASSES, EXPENSE_TYPES, INCOME_TYPES, SPENDING_CLASSES, TABLES, save_classification
from .health import financial_health
from .forecasting import estimated_forecast as calculate_estimated_forecast
from .upcoming import window_end


def number(value, optional=False):
    if optional and (value is None or value==''): return None
    result=float(value)
    if not math.isfinite(result): raise ValueError('Enter a finite amount.')
    return result


def create_blueprint(db, login_required, get_setting, latest_fx):
    bp=Blueprint('health',__name__,url_prefix='/health')

    @bp.errorhandler(ValueError)
    def invalid(exc): return render_template('planning_error.html',message=str(exc)),400

    @bp.errorhandler(TypeError)
    def invalid_type(exc): return render_template('planning_error.html',message='Enter valid financial details.'),400

    @bp.get('/')
    @login_required
    def index():
        conn=db()
        try: result=financial_health(conn,get_setting('base_currency','GBP'),latest_fx(conn))
        finally: conn.close()
        return render_template('health.html',health=result,income_types=INCOME_TYPES)

    @bp.route('/classify',methods=['GET','POST'])
    @login_required
    def classify():
        conn=db()
        try:
            table=request.values.get('table','transactions')
            if table not in (*TABLES,'accounts'): raise ValueError('Invalid record type.')
            if request.method=='POST':
                selected=request.form.getlist('selected')
                if not selected: raise ValueError('Select at least one record to classify.')
                for raw_id in selected:
                    row_id=int(raw_id)
                    if table=='accounts':
                        value=request.form.get('asset_class')
                        if value not in ASSET_CLASSES: raise ValueError('Invalid asset classification.')
                        conn.execute('UPDATE accounts SET asset_class=? WHERE id=?',(value,row_id))
                    else:
                        data={k:v for k,v in request.form.items() if v!='__keep__'}
                        save_classification(conn,table,row_id,data)
                conn.commit(); flash('Selected classifications saved. Historical amounts and categories were preserved.','ok')
                return redirect(url_for('health.classify',table=table))
            page=max(1,int(request.args.get('page',1))); query=request.args.get('q','').strip(); review=request.args.get('review')=='1'
            where=[]; params=[]
            if table=='accounts':
                sql='SELECT a.*,a.name description,a.name account,a.opening_balance amount FROM accounts a'
                if review: where.append("a.asset_class='unclassified'")
                if query: where.append('a.name LIKE ?'); params.append('%'+query+'%')
                order='a.name'
            else:
                sql=f'SELECT t.*,a.name account,a.currency,c.name category FROM {table} t JOIN accounts a ON a.id=t.account_id LEFT JOIN categories c ON c.id=t.category_id'
                if table=='transactions': where.append("COALESCE(t.transfer_group,'')=''")
                if table=='recurring_rules': where.append("t.deleted_at IS NULL AND t.transaction_type!='transfer'")
                if review:
                    where.append("(t.expense_type='unclassified' AND t.amount<0 OR t.income_type='unclassified' AND t.amount>0)" if table!='recurring_rules' else "(t.expense_type='unclassified' AND t.transaction_type='expense' OR t.income_type='unclassified' AND t.transaction_type='income')")
                if query: where.append('(t.description LIKE ? OR a.name LIKE ?)'); params.extend(['%'+query+'%']*2)
                order='t.id DESC'
            rows=conn.execute(sql+(' WHERE '+' AND '.join(where) if where else '')+f' ORDER BY {order} LIMIT 101 OFFSET ?',params+[(page-1)*100]).fetchall()
            return render_template('health_classify.html',table=table,rows=rows[:100],page=page,has_next=len(rows)>100,q=query,review=review,
                asset_classes=ASSET_CLASSES,expense_types=EXPENSE_TYPES,income_types=INCOME_TYPES,spending_classes=SPENDING_CLASSES,
                sources=conn.execute('SELECT * FROM funding_sources ORDER BY name').fetchall(),strategies=conn.execute('SELECT * FROM funding_strategies ORDER BY purpose').fetchall())
        finally: conn.close()

    @bp.route('/funding',methods=['GET','POST'])
    @login_required
    def funding():
        conn=db()
        try:
            if request.method=='POST':
                kind=request.form.get('action','strategy')
                if kind=='source':
                    name=request.form.get('name','').strip()
                    if not name or len(name)>100: raise ValueError('Enter a funding source name (up to 100 characters).')
                    source_id=request.form.get('id')
                    if conn.execute('SELECT id FROM funding_sources WHERE name=? AND id!=?',(name,int(source_id or 0))).fetchone(): raise ValueError('That funding source already exists.')
                    if source_id: conn.execute('UPDATE funding_sources SET name=? WHERE id=?',(name,int(source_id)))
                    else: conn.execute('INSERT INTO funding_sources(name) VALUES(?)',(name,))
                elif kind in ('withdrawal','capital'):
                    account_id=int(request.form['account_id'])
                    account=conn.execute('SELECT * FROM accounts WHERE id=?',(account_id,)).fetchone()
                    if not account: raise ValueError('Choose an account.')
                    day=date.fromisoformat(request.form['date']).isoformat(); amount=number(request.form['amount']); notes=request.form.get('notes','').strip()
                    if day>str(date.today()): raise ValueError('Monitoring entries must be dated today or earlier.')
                    if kind=='withdrawal':
                        net=number(request.form.get('net'),True)
                        if amount<=0 or (net is not None and (net<0 or net>amount)): raise ValueError('Enter positive gross and a net amount between zero and gross.')
                        if account['asset_class']!='retirement' and account['account_type']!='pension': raise ValueError('Choose a pension / retirement account.')
                        conn.execute('INSERT INTO pension_withdrawals(account_id,withdrawal_date,gross,net,notes) VALUES(?,?,?,?,?)',(account_id,day,amount,net,notes))
                    else:
                        entry_kind=request.form.get('kind')
                        if entry_kind not in ('opening','movement'): raise ValueError('Choose opening capital or a capital movement.')
                        if entry_kind=='opening' and conn.execute("SELECT id FROM capital_movements WHERE kind='opening' AND account_id=?",(account_id,)).fetchone(): raise ValueError('An opening entry already exists for this account. Remove it before replacing it.')
                        opening_date=conn.execute("SELECT MIN(movement_date) FROM capital_movements WHERE kind='opening'").fetchone()[0]
                        if entry_kind=='opening' and opening_date and day!=opening_date: raise ValueError('Use the same opening date for every capital account.')
                        if entry_kind=='movement' and (not opening_date or day<opening_date): raise ValueError('Record opening capital first, then movements on or after that date.')
                        conn.execute('INSERT INTO capital_movements(account_id,movement_date,amount,kind,notes) VALUES(?,?,?,?,?)',(account_id,day,amount,entry_kind,notes))
                elif kind=='remove_entry':
                    table=request.form.get('entry_table')
                    if table not in ('pension_withdrawals','capital_movements'): raise ValueError('Invalid monitoring entry.')
                    conn.execute(f'DELETE FROM {table} WHERE id=?',(int(request.form['id']),))
                elif kind=='strategy':
                    purpose=request.form.get('purpose','').strip(); amount=number(request.form.get('monthly_amount')); currency=request.form.get('currency','').strip().upper()
                    currencies={r[0] for r in conn.execute('SELECT DISTINCT currency FROM accounts')}
                    if not purpose or amount<=0 or currency not in currencies: raise ValueError('Enter a purpose, positive monthly requirement and account currency.')
                    start=request.form.get('start_date') or None; end=request.form.get('end_date') or None
                    if start: date.fromisoformat(start)
                    if end: date.fromisoformat(end)
                    if start and end and start>end: raise ValueError('End date must be on or after the start date.')
                    strategy_kind=request.form.get('kind','other')
                    if strategy_kind not in ('housing','other'): raise ValueError('Choose a strategy purpose type.')
                    strategy_id=int(request.form.get('id') or 0)
                    values=(purpose,strategy_kind,currency,amount,start,end,request.form.get('change_event','').strip(),int(request.form.get('active')=='1'))
                    if strategy_id:
                        if not conn.execute('SELECT id FROM funding_strategies WHERE id=?',(strategy_id,)).fetchone(): raise ValueError('Strategy no longer exists.')
                        conn.execute('UPDATE funding_strategies SET purpose=?,kind=?,currency=?,monthly_amount=?,start_date=?,end_date=?,change_event=?,active=? WHERE id=?',values+(strategy_id,))
                        conn.execute('DELETE FROM funding_steps WHERE strategy_id=?',(strategy_id,))
                    else: strategy_id=conn.execute('INSERT INTO funding_strategies(purpose,kind,currency,monthly_amount,start_date,end_date,change_event,active) VALUES(?,?,?,?,?,?,?,?)',values).lastrowid
                    steps=request.form.getlist('account_id'); allocations=request.form.getlist('allocation'); grosses=request.form.getlist('monthly_gross'); nets=request.form.getlist('monthly_net'); seen=set()
                    for position,raw_id in enumerate(steps):
                        if not raw_id: continue
                        aid=int(raw_id)
                        if aid in seen or not conn.execute("SELECT id FROM accounts WHERE id=? AND active=1 AND account_type!='liability'",(aid,)).fetchone(): raise ValueError('Funding accounts must be distinct active assets.')
                        seen.add(aid); allocation=number(allocations[position] if position<len(allocations) else '',True); gross=number(grosses[position] if position<len(grosses) else '',True); net=number(nets[position] if position<len(nets) else '',True)
                        if any(v is not None and v<0 for v in (allocation,gross,net)) or gross==0 or (net is not None and gross is not None and net>gross): raise ValueError('Funding allocations must be nonnegative; gross must be positive and net no greater than gross.')
                        conn.execute('INSERT INTO funding_steps(strategy_id,position,account_id,allocation,monthly_gross,monthly_net) VALUES(?,?,?,?,?,?)',(strategy_id,position,aid,allocation,gross,net))
                    if not seen: raise ValueError('Choose at least one funding account.')
                else: raise ValueError('Invalid funding action.')
                conn.commit(); flash('Funding configuration saved. Monitoring entries do not change bank or pension balances.','ok')
                return redirect(url_for('health.funding'))
            strategies=[]
            for r in conn.execute('SELECT * FROM funding_strategies ORDER BY id'):
                strategies.append(dict(r,steps=[dict(s) for s in conn.execute('SELECT * FROM funding_steps WHERE strategy_id=? ORDER BY position',(r['id'],))]))
            accounts=conn.execute('SELECT * FROM accounts ORDER BY name').fetchall()
            entries=[]
            for table,day,value in [('pension_withdrawals','withdrawal_date','gross'),('capital_movements','movement_date','amount')]:
                entries.extend(dict(r,entry_table=table) for r in conn.execute(f'SELECT t.*,a.name account,a.currency,t.{day} day,t.{value} value FROM {table} t JOIN accounts a ON a.id=t.account_id ORDER BY t.{day} DESC,t.id DESC LIMIT 100'))
            return render_template('health_funding.html',strategies=strategies,accounts=accounts,currencies=sorted({a['currency'] for a in accounts}),sources=conn.execute('SELECT * FROM funding_sources ORDER BY name').fetchall(),entries=entries,today=str(date.today()))
        finally: conn.close()

    @bp.get('/estimated-forecast')
    @login_required
    def estimated_forecast():
        today=date.today(); view=request.args.get('view','30'); end=window_end(view,today); conn=db()
        try:
            currency=get_setting('base_currency','GBP'); fx=latest_fx(conn); health=financial_health(conn,currency,fx,today)
            result=calculate_estimated_forecast(conn,today,end,currency,fx,health=health)
        finally: conn.close()
        return render_template('forecast.html',forecast=result,view=view,estimated=True,history=health['history'])
    return bp
