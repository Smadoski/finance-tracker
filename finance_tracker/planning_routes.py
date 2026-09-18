"""Planning/report routes; all financial calculations live in services."""
import json
import secrets
from datetime import date
from flask import Blueprint, request, render_template, Response, abort, session
from .forecasting import forecast
from .upcoming import upcoming, window_end
from .search import search_transactions
from .csv_io import parse_csv, preview_import, import_reviewed, export_transactions, csv_text, FIELDS
from .ai_review import financial_review, period_totals
from .target_projection import projected_targets
from .budgets import period_bounds


def dashboard_summary(conn, currency, fx):
    today=date.today(); start,end=period_bounds('monthly',today)
    projection=forecast(conn,today,end,currency,fx)
    totals=period_totals(conn,start,today,currency,fx)
    target=projected_targets(conn,'monthly',today,currency,fx)
    return dict(currency=currency,start=str(start),end=str(today),income=totals['income']['total'],expense=totals['expense']['total'],remaining=target['remaining'],**{k:projection[k] for k in ('current','projected')},upcoming_income=projection['income'],upcoming_expense=projection['expense'])


def create_blueprint(db, login_required, current_user, get_setting, latest_fx, version):
    bp=Blueprint('planning',__name__,url_prefix='/planning')

    @bp.errorhandler(ValueError)
    def invalid(exc): return render_template('planning_error.html',message=str(exc)),400

    def context(conn):
        return dict(accounts=conn.execute('SELECT id,name,currency FROM accounts WHERE active=1 ORDER BY name').fetchall(),
            categories=conn.execute('SELECT c.id,c.name,c.parent_id,p.name parent_name FROM categories c LEFT JOIN categories p ON p.id=c.parent_id ORDER BY COALESCE(p.name,c.name),c.name').fetchall(),
            users=conn.execute('SELECT id,name FROM users ORDER BY name').fetchall())

    @bp.get('/upcoming')
    @login_required
    def upcoming_view():
        today=date.today(); view=request.args.get('view','30'); end=window_end(view,today)
        conn=db()
        try: rows=upcoming(conn,today,end)
        finally: conn.close()
        return render_template('upcoming.html',rows=rows,view=view,start=today,end=end)

    @bp.get('/forecast')
    @login_required
    def forecast_view():
        today=date.today(); view=request.args.get('view','30'); end=window_end(view,today); conn=db()
        try: result=forecast(conn,today,end,get_setting('base_currency','GBP'),latest_fx(conn))
        finally: conn.close()
        return render_template('forecast.html',forecast=result,view=view)

    @bp.get('/search')
    @login_required
    def search():
        conn=db()
        try:
            page=max(1,int(request.args.get('page',1)))
            if request.args.get('format')=='csv':
                return Response(export_transactions(search_transactions(conn,request.args),get_setting('base_currency','GBP'),latest_fx(conn)),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename="transactions.csv"'})
            rows=search_transactions(conn,request.args,limit=101,offset=(page-1)*100)
            return render_template('search.html',rows=rows[:100],has_next=len(rows)>100,page=page,**context(conn))
        finally: conn.close()

    @bp.route('/import',methods=['GET','POST'])
    @login_required
    def csv_import():
        conn=db(); user=current_user()
        try:
            ctx=context(conn)
            if request.method=='GET': return render_template('csv_import.html',step='upload',**ctx)
            conn.execute("DELETE FROM csv_import_batches WHERE created_at<datetime('now','-1 day')")
            step=request.form.get('step')
            if step=='upload':
                file=request.files.get('file')
                if not file: raise ValueError('Select a CSV file.')
                source=parse_csv(file.read(2*1024*1024+1)); token=secrets.token_urlsafe(32)
                conn.execute('INSERT INTO csv_import_batches(token,user_id,payload) VALUES(?,?,?)',(token,user['id'],json.dumps(dict(source=source))))
                conn.commit()
                return render_template('csv_import.html',step='map',source=source,token=token,fields=FIELDS,**ctx)
            token=request.form.get('token','')
            # Serialises final review/import so double-submit cannot import a batch twice.
            conn.commit(); conn.execute('BEGIN IMMEDIATE')
            batch=conn.execute('SELECT * FROM csv_import_batches WHERE token=? AND user_id=?',(token,user['id'])).fetchone()
            if not batch: raise ValueError('Import expired or already completed. Select the file again.')
            payload=json.loads(batch['payload'])
            if step=='review':
                mapping={f:request.form.get('map_'+f,'') for f in FIELDS}; account_id=int(request.form.get('account_id','0')); date_format=request.form.get('date_format','%Y-%m-%d')
                rows=preview_import(conn,payload['source'],mapping,account_id,date_format)
                payload.update(mapping=mapping,account_id=account_id,date_format=date_format,rows=rows)
                conn.execute('UPDATE csv_import_batches SET payload=?,reviewed=1 WHERE token=?',(json.dumps(payload),token)); conn.commit()
                return render_template('csv_import.html',step='review',rows=rows,token=token,**ctx)
            if step!='import' or not batch['reviewed']: raise ValueError('Preview and review the mapped transactions first.')
            rows=preview_import(conn,payload['source'],payload['mapping'],payload['account_id'],payload['date_format'])
            if rows!=payload['rows']:
                payload['rows']=rows; conn.execute('UPDATE csv_import_batches SET payload=? WHERE token=?',(json.dumps(payload),token)); conn.commit()
                return render_template('csv_import.html',step='review',rows=rows,token=token,changed=True,**ctx)
            summary=import_reviewed(conn,rows,set(request.form.getlist('selected')),set(request.form.getlist('duplicate')),user['id'])
            conn.execute('DELETE FROM csv_import_batches WHERE token=?',(token,)); conn.commit()
            return render_template('csv_import.html',step='complete',summary=summary,**ctx)
        finally: conn.close()

    @bp.get('/ai-review')
    @login_required
    def ai_review():
        conn=db()
        try:
            period=request.args.get('period','monthly'); reference=request.args.get('date',date.today().isoformat())
            ids=[int(v) for v in request.args.getlist('account_id')]; history=int(request.args.get('history','0'))
            horizons=request.args.getlist('horizon')
            if request.args.get('format')=='json':
                result=financial_review(conn,period,reference,get_setting('base_currency','GBP'),latest_fx(conn),version,ids,history,horizons)
                return Response(json.dumps(result,indent=2,allow_nan=False),mimetype='application/json',headers={'Content-Disposition':'attachment; filename="financial-review.json"'})
            return render_template('ai_review.html',today=date.today().isoformat(),**context(conn))
        finally: conn.close()

    @bp.get('/targets.csv')
    @login_required
    def targets_csv():
        conn=db()
        try:
            r=projected_targets(conn,request.args.get('period','monthly'),request.args.get('date',date.today().isoformat()),get_setting('base_currency','GBP'),latest_fx(conn),[int(v) for v in request.args.getlist('account_id')])
            body=csv_text(['Category','Currency','Target','Actual','Remaining','Percent used','Status','Projected','Included in overall'],([x['name'],r['currency'],x['target'],x['actual'],x['remaining'],x['used'],x['status'],x['projected'],x['included_in_overall']] for x in r['rows']))
            return Response(body,mimetype='text/csv',headers={'Content-Disposition':'attachment; filename="targets.csv"'})
        finally: conn.close()
    return bp
