"""Preserves target actuals and most-specific aggregation; adds scheduled commitments."""
from datetime import date
from .budgets import target_report
from .upcoming import upcoming
from .money import convert


def projected_targets(conn, period, reference, currency, fx, account_ids=None, today=None):
    today=today or date.today()
    report=target_report(conn,period,reference,currency,fx,account_ids)
    items=upcoming(conn,max(today,report['start']),report['end'],account_ids)
    parents={r['id']:r['parent_id'] for r in conn.execute('SELECT id,parent_id FROM categories')}
    names={r['id']:r['name'] for r in conn.execute('SELECT id,name FROM categories')}
    for row in report['rows']:
        row['group']=names.get(parents.get(row['category_id'])) or names[row['category_id']]
        remaining=sum(convert(i['amount'],i['currency'],currency,fx) for i in items
            if i['type']=='expense' and (not account_ids or i['account_id'] in account_ids)
            and (i['category_id']==row['category_id'] or parents.get(i['category_id'])==row['category_id']))
        row.update(remaining=row['target']-row['actual'],projected=row['actual']+remaining,
            projection_status='Likely to exceed target' if row['actual']<=row['target']<row['actual']+remaining else row['status'])
    report['remaining']=report['target']-report['actual']
    report['projected']=sum(r['projected'] for r in report['rows'] if r['included_in_overall'])
    report['method']='Projected expenditure = posted target actuals + unposted scheduled expenses remaining in this period. Unscheduled spending is not predicted. Most-specific targets determine overall totals.'
    return report
