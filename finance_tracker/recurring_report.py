"""Filtered recurring report with Decimal normalisation and currency-safe totals."""
from decimal import Decimal
from .frequencies import FREQUENCY_LABELS, equivalents
from .money import convert
from .recurring import adjust_working_day


def recurring_report(conn, filters, base, fx):
    where=['r.deleted_at IS NULL']; params=[]
    for key,column in [('account_id','r.account_id'),('category_id','r.category_id')]:
        if filters.get(key):
            if key=='category_id': where.append('(c.id=? OR c.parent_id=?)'); params.extend([int(filters[key])]*2)
            else: where.append(column+'=?'); params.append(int(filters[key]))
    for key,column,allowed in [('currency','a.currency',('GBP','EUR')),('frequency','r.frequency',FREQUENCY_LABELS),('status','r.active',('active','inactive'))]:
        value=filters.get(key)
        if value:
            if value not in allowed: raise ValueError('Invalid '+key+' filter.')
            where.append(column+'=?'); params.append(int(value=='active') if key=='status' else value)
    rows=[]; groups={}; totals={kind:{'monthly':Decimal(0),'annual':Decimal(0)} for kind in ('expense','income','transfer')}
    for raw in conn.execute('''SELECT r.*,a.name account,a.currency,c.name category,p.name parent_category,
        ta.name destination,ta.currency destination_currency FROM recurring_rules r JOIN accounts a ON a.id=r.account_id
        LEFT JOIN accounts ta ON ta.id=r.to_account_id LEFT JOIN categories c ON c.id=r.category_id
        LEFT JOIN categories p ON p.id=c.parent_id WHERE '''+' AND '.join(where)+' ORDER BY r.frequency,a.currency,r.description',params):
        row=dict(raw); amount=Decimal(str(row['amount'])); monthly,annual=equivalents(amount,row['frequency'])
        row.update(amount=amount,monthly=monthly,annual=annual,frequency_label=FREQUENCY_LABELS[row['frequency']],
            next_payment=str(adjust_working_day(row['next_scheduled_date'],row['working_day_adjustment'],row.get('holiday_calendar','weekdays'))))
        key=(row['frequency'],row['currency'],row['transaction_type'])
        groups[key]=groups.get(key,Decimal(0))+amount
        totals[row['transaction_type']]['monthly']+=convert(monthly,row['currency'],base,fx)
        totals[row['transaction_type']]['annual']+=convert(annual,row['currency'],base,fx)
        rows.append(row)
    return dict(rows=rows,groups=[dict(frequency=FREQUENCY_LABELS[f],currency=c,type=t,amount=v) for (f,c,t),v in groups.items()],totals=totals,
        base=base,fx=fx,monthly=filters.get('monthly')=='1',annual=filters.get('annual')=='1',filters=dict(filters),
        method='Equivalents use 365 daily, 52 weekly, 26 fortnightly or 13 four-weekly payments per year. Calendar-month frequencies use 12, quarterly 4, six-monthly 2 and annual 1. These are normalised costs, not a count of payments in a calendar year. Totals include the displayed active/inactive records; income and transfers are separate from expenditure.')


def export_columns(report):
    headers=['Payee','Category','Account','Type','Amount','Currency','Frequency','Next payment','Status']
    if report['monthly']: headers.append('Monthly equivalent')
    if report['annual']: headers.append('Annual equivalent')
    rows=[]
    for r in report['rows']:
        row=[r['description'],' / '.join(filter(None,[r['parent_category'],r['category']])),r['account'],r['transaction_type'],format(r['amount'],'.2f'),r['currency'],r['frequency_label'],r['next_payment'],'Active' if r['active'] else 'Inactive']
        if report['monthly']: row.append(format(r['monthly'],'.2f'))
        if report['annual']: row.append(format(r['annual'],'.2f'))
        rows.append(row)
    return headers,rows
