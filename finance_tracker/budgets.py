"""Category target periods, actuals, and non-overlapping aggregation."""

from datetime import date, timedelta

from .money import convert


def period_bounds(period, reference=None):
    reference=reference or date.today()
    if not isinstance(reference,date): reference=date.fromisoformat(str(reference))
    if period=='weekly':
        start=reference-timedelta(days=reference.weekday()); return start,start+timedelta(days=6)
    if period=='monthly':
        start=reference.replace(day=1)
        next_month=(start.replace(day=28)+timedelta(days=4)).replace(day=1)
        return start,next_month-timedelta(days=1)
    if period=='quarterly':
        month=((reference.month-1)//3)*3+1; start=date(reference.year,month,1)
        next_q=date(reference.year+1,1,1) if month==10 else date(reference.year,month+3,1)
        return start,next_q-timedelta(days=1)
    if period=='yearly': return date(reference.year,1,1),date(reference.year,12,31)
    raise ValueError('Unsupported target period.')


def category_actual(conn, category_id, start, end, output_currency, fx, account_ids=None):
    category=conn.execute('SELECT id,parent_id FROM categories WHERE id=?',(category_id,)).fetchone()
    if not category: return 0.0
    params=[category_id,category_id,start.isoformat(),end.isoformat()]
    account_sql=''
    if account_ids:
        marks=','.join('?' for _ in account_ids); account_sql=f' AND t.account_id IN ({marks})'; params.extend(account_ids)
    rows=conn.execute(f"""SELECT t.amount,a.currency FROM transactions t JOIN accounts a ON a.id=t.account_id
                         JOIN categories c ON c.id=t.category_id
                         WHERE (c.id=? OR c.parent_id=?) AND c.kind='expense'
                           AND t.tx_date BETWEEN ? AND ? {account_sql}""",params).fetchall()
    return sum(abs(convert(row['amount'],row['currency'],output_currency,fx)) for row in rows)


def target_report(conn, period, reference, output_currency, fx, account_ids=None):
    start,end=period_bounds(period,reference)
    targets=conn.execute("""SELECT t.*,c.name category_name,c.parent_id,p.name parent_name
                            FROM category_targets t JOIN categories c ON c.id=t.category_id
                            LEFT JOIN categories p ON p.id=c.parent_id
                            WHERE t.active=1 AND t.period=? ORDER BY COALESCE(p.name,c.name),c.parent_id,c.name""",(period,)).fetchall()
    child_target_parents={row['parent_id'] for row in targets if row['parent_id'] is not None}
    rows=[]; overall_target=overall_actual=0.0
    for target in targets:
        target_value=convert(target['target_amount'],target['currency'],output_currency,fx)
        actual=category_actual(conn,target['category_id'],start,end,output_currency,fx,account_ids)
        variance=actual-target_value; used=(actual/target_value*100) if target_value else (0 if actual==0 else None)
        status='Exact target' if abs(variance)<0.005 else ('Over target' if variance>0 else 'Under target')
        included=not (target['parent_id'] is None and target['category_id'] in child_target_parents)
        if included: overall_target+=target_value; overall_actual+=actual
        rows.append(dict(target_id=target['id'],category_id=target['category_id'],name=f"{target['parent_name']} / {target['category_name']}" if target['parent_name'] else target['category_name'],
                         is_parent=target['parent_id'] is None,target=target_value,actual=actual,variance=variance,used=used,status=status,included_in_overall=included))
    overall_variance=overall_actual-overall_target
    overall_status='Exact target' if abs(overall_variance)<0.005 else ('Over target' if overall_variance>0 else 'Under target')
    return dict(period=period,start=start,end=end,currency=output_currency,rows=rows,target=overall_target,actual=overall_actual,
                variance=overall_variance,used=(overall_actual/overall_target*100 if overall_target else (0 if overall_actual==0 else None)),status=overall_status)

