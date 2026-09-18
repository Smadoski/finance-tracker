"""Allowlisted calculated financial export; no raw settings, users or application internals."""
from datetime import date, datetime, timezone
from .accounts import account_balance
from .money import convert
from .budgets import period_bounds
from .target_projection import projected_targets
from .recurring import month_shift
from .forecasting import forecast
from .upcoming import upcoming, window_end
from .search import search_transactions


def period_totals(conn, start, end, currency, fx, account_ids=None):
    totals={kind:dict(total=0.0,by_category={},by_subcategory={},by_account={}) for kind in ('income','expense')}
    for row in search_transactions(conn,dict(start=str(start),end=str(end))):
        if row['type']=='transfer' or (account_ids and row['account_id'] not in account_ids): continue
        amount=abs(convert(row['amount'],row['currency'],currency,fx)); group=totals[row['type']]
        group['total']+=amount
        for field,key in (('by_category','category'),('by_subcategory','subcategory'),('by_account','account')):
            label=row[key]
            if label: group[field][label]=group[field].get(label,0)+amount
    return totals


def financial_review(conn, period, reference, currency, fx, version, account_ids=None, history=0, horizons=('30','60','90'), today=None):
    today=today or date.today(); start,end=period_bounds(period,reference)
    if history not in (0,3,6,12): raise ValueError('Choose 0, 3, 6 or 12 months of history.')
    if any(str(h) not in ('30','60','90') for h in horizons): raise ValueError('Invalid forecast horizon.')
    accounts=[]
    for a in conn.execute('SELECT * FROM accounts WHERE active=1 ORDER BY name'):
        if account_ids and a['id'] not in account_ids: continue
        balance=account_balance(conn,a)
        accounts.append(dict(name=a['name'],type=a['account_type'],currency=a['currency'],current_balance=balance,equivalent_balance=convert(balance,a['currency'],currency,fx)))
    totals=period_totals(conn,start,min(end,today),currency,fx,account_ids)
    targets=projected_targets(conn,period,reference,currency,fx,account_ids,today)
    # Explicit allowlist removes target/category primary keys as well as implementation flags.
    target_data={k:targets[k] for k in ('period','currency','target','actual','variance','used','status','remaining','projected','method')}
    target_data['categories']=[{k:r[k] for k in ('name','target','actual','variance','used','status','remaining','projected','projection_status','included_in_overall')} for r in targets['rows']]
    future=upcoming(conn,max(today,start),end,account_ids)
    future_data=[{k:r[k] for k in ('due_date','description','account','currency','amount','destination','destination_currency','to_amount','type','category','subcategory','posting_mode','status')} for r in future]
    for kind in ('income','expense'):
        totals[kind]['recurring_remaining']=sum(convert(r['amount'],r['currency'],currency,fx) for r in future if r['type']==kind and (not account_ids or r['account_id'] in account_ids))
    projections={h:forecast(conn,today,window_end(h,today),currency,fx,account_ids) for h in ('month',*horizons)}
    for projection in projections.values():
        for account in projection['accounts']:
            account.pop('account_id')
            account['transactions']=[{k:r[k] for k in ('due_date','description','type','effect','status')} for r in account['transactions']]
    history_rows=[]; month=start.replace(day=1)
    for n in range(history,0,-1):
        hstart=month_shift(month,-n,1); hend=period_bounds('monthly',hstart)[1]
        values=period_totals(conn,hstart,hend,currency,fx,account_ids)
        history_rows.append(dict(start=str(hstart),end=str(hend),**values))
    observed=[r for r in history_rows if r['income']['total'] or r['expense']['total']]
    averages={}; trend=None
    if observed:
        categories={c for r in observed for c in r['expense']['by_category']}
        averages={c:sum(r['expense']['by_category'].get(c,0) for r in observed)/len(observed) for c in categories}
    if len(observed)>=3:
        first,last=observed[0],observed[-1]
        trend={kind:dict(absolute_change=last[kind]['total']-first[kind]['total'],percent_change=(last[kind]['total']/first[kind]['total']-1)*100 if first[kind]['total'] else None) for kind in ('income','expense')}
        trend['categories']={c:last['expense']['by_category'].get(c,0)-first['expense']['by_category'].get(c,0) for c in averages}
    previous_start=month_shift(today.replace(day=1),-1,1)
    elapsed_end=previous_start.replace(day=min(today.day,period_bounds('monthly',previous_start)[1].day))
    return dict(metadata=dict(version=version,exported_at=datetime.now(timezone.utc).isoformat(),period=period,start=str(start),end=str(end),as_of=str(today),equivalent_currency=currency,account_currencies=sorted({a['currency'] for a in accounts}),gbp_eur_rate=fx),
        accounts=accounts,period_income=totals['income'],period_expenditure=totals['expense'],targets=target_data,recurring=future_data,forecast=projections,
        historical_context=dict(months_requested=history,months_with_activity=len(observed),periods=history_rows,average_category_spend=averages,trend=trend,
            current_month_to_date=period_totals(conn,today.replace(day=1),today,currency,fx,account_ids),
            previous_month_same_days=period_totals(conn,previous_start,elapsed_end,currency,fx,account_ids),
            method='Historical averages use months with recorded activity; empty months may represent missing data. Trends require at least three active months and compare first with last. Month-to-date comparison uses the same elapsed days.'))
