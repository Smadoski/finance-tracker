"""Deterministic projections; never posts transactions or changes balances."""
from .accounts import account_balance
from .money import convert
from .upcoming import upcoming

CASH_TYPES=('current','savings','premium_bonds','cash')


def forecast(conn, start, end, currency, fx, account_ids=None):
    accounts=[dict(a) for a in conn.execute('SELECT * FROM accounts WHERE active=1 ORDER BY name')
              if a['account_type'] in CASH_TYPES and (not account_ids or a['id'] in account_ids)]
    items=upcoming(conn,start,end,account_ids)
    result=[]
    for account in accounts:
        balance=account_balance(conn,account); income=expense=transfers=0.0; contributors=[]
        for item in items:
            effect=0.0
            if item['account_id']==account['id']:
                amount=float(item['amount'])
                if item['type']=='income': income+=amount; effect+=amount
                elif item['type']=='expense': expense+=amount; effect-=amount
                else: transfers-=amount; effect-=amount
            if item['type']=='transfer' and item['to_account_id']==account['id']:
                transfers+=float(item['to_amount']); effect+=float(item['to_amount'])
            if effect: contributors.append(dict(item,effect=effect))
        result.append(dict(account_id=account['id'],account=account['name'],currency=account['currency'],current=balance,
            income=income,expense=expense,transfers=transfers,projected=balance+income-expense+transfers,transactions=contributors))
    combined={key:sum(convert(a[key],a['currency'],currency,fx) for a in result) for key in ('current','income','expense','transfers','projected')}
    return dict(start=str(start),end=str(end),currency=currency,accounts=result,**combined,
        method='Current posted balance plus unposted scheduled income, minus scheduled expenses, plus net scheduled transfers. Pending review items are assumed to post on their due date. No unscheduled spending or exchange-rate changes are predicted.')


def estimated_forecast(conn, start, end, currency, fx, account_ids=None, health=None):
    """Add only the historical normal residual to the existing scheduled projection."""
    from .health import financial_health
    health=health or financial_health(conn,currency,fx,start,account_ids)
    result=forecast(conn,start,end,currency,fx,account_ids)
    days=max((end-start).days+1,0)
    for account in result['accounts']:
        extra=health['estimated_additional_monthly_by_account'].get(str(account['account_id']),0)*days/(365.25/12)
        account['estimated_additional']=convert(extra,currency,account['currency'],fx)
        account['projected']-=account['estimated_additional']
    result['estimated_additional']=sum(convert(a['estimated_additional'],a['currency'],currency,fx) for a in result['accounts'])
    result['projected']-=result['estimated_additional']
    result['history']=health['history']
    result['method']='Known scheduled cash flows plus estimated unscheduled normal expenditure. Capital purchases are never extrapolated; known scheduled capital purchases remain scheduled cash flows. Extraordinary receipts are never extrapolated. Historical residuals are prorated by days / (365.25/12). '+health['history']['method']
    return result
