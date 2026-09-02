"""Flask routes for recurring financial activity."""

from datetime import date
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from .recurring import advance_rule, post_pending_transfer, process_due, process_rule_occurrence, validate_rule


def create_blueprint(db, login_required, current_user, category_options):
    bp=Blueprint('recurring',__name__,url_prefix='/recurring')

    @bp.route('/',methods=['GET','POST'])
    @login_required
    def index():
        conn=db()
        if request.method=='POST':
            try:
                form=dict(request.form)
                form['active']=request.form.get('active')=='1'
                values=validate_rule(conn,form)
                user=current_user()
                conn.execute("""INSERT INTO recurring_rules(description,transaction_type,account_id,to_account_id,amount,to_amount,category_id,start_date,end_date,next_scheduled_date,frequency,working_day_adjustment,posting_mode,active,created_by)
                                VALUES(:description,:transaction_type,:account_id,:to_account_id,:amount,:to_amount,:category_id,:start_date,:end_date,:next_scheduled_date,:frequency,:working_day_adjustment,:posting_mode,:active,:created_by)""",
                             dict(values,created_by=user['id']))
                conn.commit(); flash('Recurring transaction added.','ok')
            except (ValueError,TypeError) as exc:
                conn.rollback(); flash(str(exc),'error')
        rules=conn.execute("""SELECT r.*,a.name account_name,a.currency,ta.name to_account_name,c.name category_name,p.name parent_category_name
                              FROM recurring_rules r JOIN accounts a ON a.id=r.account_id
                              LEFT JOIN accounts ta ON ta.id=r.to_account_id LEFT JOIN categories c ON c.id=r.category_id
                              LEFT JOIN categories p ON p.id=c.parent_id WHERE r.deleted_at IS NULL
                              ORDER BY r.active DESC,r.next_scheduled_date,r.description""").fetchall()
        history=conn.execute("""SELECT o.*,r.description,r.transaction_type FROM recurring_occurrences o
                                JOIN recurring_rules r ON r.id=o.rule_id ORDER BY o.created_at DESC,o.id DESC LIMIT 100""").fetchall()
        accounts=conn.execute("SELECT id,name,currency FROM accounts WHERE active=1 AND account_type NOT IN ('pension','other_asset','liability') ORDER BY name").fetchall()
        categories=category_options(conn,('expense','income')); conn.close()
        return render_template('recurring.html',rules=rules,history=history,accounts=accounts,categories=categories,today=date.today().isoformat())

    @bp.post('/<int:rule_id>/toggle')
    @login_required
    def toggle(rule_id):
        conn=db(); row=conn.execute('SELECT active FROM recurring_rules WHERE id=?',(rule_id,)).fetchone()
        if not row: conn.close(); abort(404)
        conn.execute('UPDATE recurring_rules SET active=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(0 if row['active'] else 1,rule_id)); conn.commit(); conn.close()
        flash('Recurring transaction status updated.','ok'); return redirect(url_for('recurring.index'))

    @bp.route('/<int:rule_id>/edit',methods=['GET','POST'])
    @login_required
    def edit(rule_id):
        conn=db(); rule=conn.execute('SELECT * FROM recurring_rules WHERE id=?',(rule_id,)).fetchone()
        if not rule: conn.close(); abort(404)
        if request.method=='POST':
            try:
                form=dict(request.form)
                form['active']=request.form.get('active')=='1'
                values=validate_rule(conn,form)
                values['id']=rule_id
                conn.execute("""UPDATE recurring_rules SET description=:description,transaction_type=:transaction_type,
                                account_id=:account_id,to_account_id=:to_account_id,amount=:amount,to_amount=:to_amount,
                                category_id=:category_id,start_date=:start_date,end_date=:end_date,
                                next_scheduled_date=:next_scheduled_date,frequency=:frequency,
                                working_day_adjustment=:working_day_adjustment,posting_mode=:posting_mode,
                                active=:active,updated_at=CURRENT_TIMESTAMP WHERE id=:id""",values)
                conn.commit(); conn.close(); flash('Recurring transaction updated.','ok'); return redirect(url_for('recurring.index'))
            except (ValueError,TypeError) as exc:
                conn.rollback(); flash(str(exc),'error')
        accounts=conn.execute("SELECT id,name,currency FROM accounts WHERE active=1 AND account_type NOT IN ('pension','other_asset','liability') ORDER BY name").fetchall()
        categories=category_options(conn,('expense','income')); rule=conn.execute('SELECT * FROM recurring_rules WHERE id=?',(rule_id,)).fetchone(); conn.close()
        return render_template('recurring_edit.html',rule=rule,accounts=accounts,categories=categories)

    @bp.post('/<int:rule_id>/delete')
    @login_required
    def delete(rule_id):
        conn=db(); row=conn.execute('SELECT id FROM recurring_rules WHERE id=?',(rule_id,)).fetchone()
        if not row: conn.close(); abort(404)
        conn.execute("UPDATE recurring_rules SET active=0,deleted_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE id=?",(rule_id,)); conn.commit(); conn.close(); flash('Recurring rule deleted. Its audit history was retained.','ok')
        return redirect(url_for('recurring.index'))

    @bp.post('/<int:rule_id>/skip')
    @login_required
    def skip(rule_id):
        conn=db(); rule=conn.execute('SELECT * FROM recurring_rules WHERE id=?',(rule_id,)).fetchone()
        if not rule: conn.close(); abort(404)
        scheduled=rule['next_scheduled_date']; process_rule_occurrence(conn,rule,scheduled,status_override='skipped'); advance_rule(conn,rule,scheduled); conn.commit(); conn.close()
        flash('Next scheduled occurrence skipped.','ok'); return redirect(url_for('recurring.index'))

    @bp.post('/<int:rule_id>/post-now')
    @login_required
    def post_now(rule_id):
        conn=db(); rule=conn.execute('SELECT * FROM recurring_rules WHERE id=?',(rule_id,)).fetchone()
        if not rule: conn.close(); abort(404)
        scheduled=rule['next_scheduled_date']; process_rule_occurrence(conn,rule,scheduled,force_post=True); advance_rule(conn,rule,scheduled); conn.commit(); conn.close()
        flash('Scheduled occurrence posted now.','ok'); return redirect(url_for('recurring.index'))

    @bp.post('/occurrence/<int:occurrence_id>/post-transfer')
    @login_required
    def post_transfer(occurrence_id):
        conn=db()
        try: post_pending_transfer(conn,occurrence_id); flash('Pending scheduled transfer posted.','ok')
        except ValueError as exc: flash(str(exc),'error')
        finally: conn.close()
        return redirect(url_for('recurring.index'))

    @bp.post('/process')
    @login_required
    def process():
        conn=db(); items=process_due(conn); conn.close(); flash(f'Processed {len(items)} due occurrence(s).','ok'); return redirect(url_for('recurring.index'))

    return bp
