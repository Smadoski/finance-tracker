"""Flask routes for category targets and budget reporting."""

import sqlite3

from datetime import date
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from .budgets import target_report


def create_blueprint(db, login_required, current_user, category_options, get_setting, latest_fx):
    bp=Blueprint('budgets',__name__,url_prefix='/budgets')

    @bp.route('/',methods=['GET','POST'])
    @login_required
    def index():
        conn=db()
        if request.method=='POST':
            try:
                category_id=int(request.form['category_id']); amount=abs(float(request.form['target_amount']))
                period=request.form['period']; currency=request.form['currency']
                category=conn.execute("SELECT id FROM categories WHERE id=? AND kind='expense'",(category_id,)).fetchone()
                if not category or period not in ('weekly','monthly','quarterly','yearly') or currency not in ('GBP','EUR'): raise ValueError('Choose valid target options.')
                user=current_user(); active=1 if request.form.get('active','1')=='1' else 0
                conn.execute("""INSERT INTO category_targets(category_id,target_amount,currency,period,active,created_by)
                                VALUES(?,?,?,?,?,?) ON CONFLICT(category_id,period) DO UPDATE SET
                                target_amount=excluded.target_amount,currency=excluded.currency,active=excluded.active,updated_at=CURRENT_TIMESTAMP""",
                             (category_id,amount,currency,period,active,user['id']))
                conn.commit(); flash('Category target saved.','ok')
            except (ValueError,TypeError,KeyError) as exc:
                conn.rollback(); flash(str(exc),'error')
        targets=conn.execute("""SELECT t.*,c.name category_name,c.parent_id,p.name parent_name FROM category_targets t
                                JOIN categories c ON c.id=t.category_id LEFT JOIN categories p ON p.id=c.parent_id
                                ORDER BY t.active DESC,t.period,COALESCE(p.name,c.name),c.name""").fetchall()
        categories=category_options(conn,('expense',)); conn.close()
        return render_template('budgets.html',targets=targets,categories=categories,base=get_setting('base_currency','GBP'))

    @bp.post('/<int:target_id>/toggle')
    @login_required
    def toggle(target_id):
        conn=db(); row=conn.execute('SELECT active FROM category_targets WHERE id=?',(target_id,)).fetchone()
        if not row: conn.close(); abort(404)
        conn.execute('UPDATE category_targets SET active=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(0 if row['active'] else 1,target_id)); conn.commit(); conn.close(); return redirect(url_for('budgets.index'))

    @bp.route('/<int:target_id>/edit',methods=['GET','POST'])
    @login_required
    def edit(target_id):
        conn=db(); target=conn.execute('SELECT * FROM category_targets WHERE id=?',(target_id,)).fetchone()
        if not target: conn.close(); abort(404)
        if request.method=='POST':
            try:
                category_id=int(request.form['category_id']); amount=abs(float(request.form['target_amount'])); period=request.form['period']; currency=request.form['currency']
                category=conn.execute("SELECT id FROM categories WHERE id=? AND kind='expense'",(category_id,)).fetchone()
                if not category or period not in ('weekly','monthly','quarterly','yearly') or currency not in ('GBP','EUR'): raise ValueError('Choose valid target options.')
                conn.execute('UPDATE category_targets SET category_id=?,target_amount=?,currency=?,period=?,active=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',
                             (category_id,amount,currency,period,1 if request.form.get('active')=='1' else 0,target_id)); conn.commit(); conn.close(); flash('Category target updated.','ok'); return redirect(url_for('budgets.index'))
            except (ValueError,TypeError,KeyError,sqlite3.IntegrityError) as exc:
                conn.rollback(); flash(str(exc),'error')
        target=conn.execute('SELECT * FROM category_targets WHERE id=?',(target_id,)).fetchone(); categories=category_options(conn,('expense',)); conn.close()
        return render_template('budget_edit.html',target=target,categories=categories)

    @bp.post('/<int:target_id>/delete')
    @login_required
    def delete(target_id):
        conn=db(); conn.execute('DELETE FROM category_targets WHERE id=?',(target_id,)); conn.commit(); conn.close(); flash('Category target deleted.','ok'); return redirect(url_for('budgets.index'))

    @bp.get('/report')
    @login_required
    def report():
        period=request.args.get('period','monthly'); reference=request.args.get('date') or date.today().isoformat(); output=get_setting('base_currency','GBP')
        account_ids=sorted({int(x) for x in request.args.getlist('account_id') if x.isdigit()})
        conn=db(); fx=latest_fx(conn); result=target_report(conn,period,reference,output,fx,account_ids)
        accounts=conn.execute("SELECT id,name,currency FROM accounts WHERE active=1 AND account_type NOT IN ('pension','other_asset','liability') ORDER BY name").fetchall(); conn.close()
        return render_template('budget_report.html',report=result,accounts=accounts,selected_account_ids=account_ids,reference=reference)

    return bp
