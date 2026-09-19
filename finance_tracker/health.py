"""Read-only financial-health calculations. Values retain the account's currency until conversion."""
from collections import defaultdict
from datetime import date, timedelta
from .accounts import account_balance
from .classifications import INCOME_TYPES
from .frequencies import equivalents
from .recurring import month_shift
from .money import convert_known as converted, rates_in_eur


def scenario(model, enabled=None):
    enabled = set(enabled if enabled is not None else [s['key'] for s in model['income_sources'] if s['type']!='extraordinary'])
    income = sum(s['monthly'] for s in model['income_sources'] if s['key'] in enabled and s['type']!='extraordinary')
    extraordinary = sum(s['monthly'] for s in model['income_sources'] if s['key'] in enabled and s['type']=='extraordinary')
    cost = model['normal_monthly_cost']; surplus = income-cost; drawdown=max(-surplus,0)
    capital = model['available_financial_capital']
    return dict(monthly_income=income,normal_monthly_cost=cost,monthly_surplus=surplus,annual_surplus=surplus*12,
                income_coverage=income/cost*100 if cost else None,monthly_capital_requirement=drawdown,
                annual_capital_requirement=drawdown*12,financial_capital_runway_months=capital/drawdown if drawdown else None,
                extraordinary_monthly_observed=extraordinary,
                method='Scenario uses cached monthly equivalents. Extraordinary receipts stay outside income coverage. Runway excludes pensions and other assets; assumes constant spending and exchange rates, no returns.')


def funding_projection(conn, accounts, fx, today):
    results=[]; selected={a['id']:a for a in accounts}
    shared={row['account_id'] for row in conn.execute('''SELECT f.account_id FROM funding_steps f JOIN funding_strategies s ON s.id=f.strategy_id WHERE s.active=1 AND (s.end_date IS NULL OR s.end_date>=?) GROUP BY f.account_id HAVING COUNT(*)>1''',(str(today),))}
    for raw in conn.execute('SELECT * FROM funding_strategies WHERE active=1 ORDER BY id'):
        strategy=dict(raw); steps=list(conn.execute('SELECT * FROM funding_steps WHERE strategy_id=? ORDER BY position',(strategy['id'],)))
        if not steps or any(s['account_id'] not in selected for s in steps): continue
        start=max(today,date.fromisoformat(strategy['start_date']) if strategy['start_date'] else today)
        end=date.fromisoformat(strategy['end_date']) if strategy['end_date'] else None
        requirement=strategy['monthly_amount']; elapsed=0; rows=[]
        for step in steps:
            account=selected[step['account_id']]; balance=max(account['balance'],0)
            designated=min(balance,step['allocation']) if step['allocation'] is not None else balance
            available=converted(designated,account['currency'],strategy['currency'],fx)
            pension=account['asset_class']=='retirement' or account['account_type']=='pension'
            gross=step['monthly_gross'] if pension and step['monthly_gross'] is not None else converted(requirement,strategy['currency'],account['currency'],fx)
            net=step['monthly_net']; needed=converted(requirement,strategy['currency'],account['currency'],fx)
            months=designated/gross if pension and gross else available/requirement
            begins=start+timedelta(days=round(elapsed*365.25/12))
            limit=max((end-begins).days+1,0)/(365.25/12) if end else months
            used_months=min(months,limit)
            transition=begins+timedelta(days=round(used_months*365.25/12))
            cumulative=conn.execute('SELECT COALESCE(SUM(gross),0) FROM pension_withdrawals WHERE account_id=? AND withdrawal_date<=?',(account['id'],str(today))).fetchone()[0]
            rows.append(dict(account=account['name'],currency=account['currency'],asset_class=account['asset_class'],balance=account['balance'],
                designated_balance=designated,equivalent_balance=available,runway_months=months,months_used_before_end=used_months,
                starts=str(begins),transition_date=str(transition) if used_months else None,estimated_monthly_gross=gross if pension else None,
                monthly_net=net,net_requirement=needed if pension else None,net_shortfall=max(needed-net,0) if pension and net is not None else None,
                annual_gross=gross*12 if pension else None,withdrawal_percent=gross*12/balance*100 if pension and balance else None,
                cumulative_gross_withdrawals=cumulative if pension else None,projected_gross_requirement=gross*used_months if pension else None))
            elapsed+=used_months
        current=next((r for r in rows if r['months_used_before_end']>0),None)
        index=rows.index(current) if current else -1
        results.append(dict(purpose=strategy['purpose'],kind=strategy['kind'],currency=strategy['currency'],monthly_requirement=requirement,
            start_date=str(start),end_date=strategy['end_date'],change_event=strategy['change_event'],sources=rows,
            current_source=current,next_source=next((r for r in rows[index+1:] if r['months_used_before_end']>0),None) if index>=0 else None,
            combined_runway_months=elapsed,available_balance=sum(r['equivalent_balance'] for r in rows),
            allocation_warning='Some accounts also fund another active strategy. These runways cannot be added; review allocations against the available balances.' if any(s['account_id'] in shared for s in steps) else None,
            status='Ended' if end and end<today else ('Starts in future' if start>today else 'Active'),
            method='Estimate from current designated balances, constant monthly withdrawals and current FX; fractional months use 365.25/12 days. End date caps funding. Pension gross defaults to required cash before unknown tax; enter known gross/net amounts. Shared account allocations are not additive.'))
    return results


def financial_health(conn, currency, fx, today=None, account_ids=None):
    today=today or date.today(); end=today.replace(day=1); start=month_shift(end,-12,1)
    accounts=[]; totals=defaultdict(float); buckets=defaultdict(float)
    for raw in conn.execute('SELECT * FROM accounts WHERE active=1 ORDER BY name'):
        if account_ids and raw['id'] not in account_ids: continue
        a=dict(raw); balance=account_balance(conn,a); signed=-abs(balance) if a['account_type']=='liability' else balance
        amount=converted(signed,a['currency'],currency,fx)
        accounts.append(dict(id=a['id'],name=a['name'],account_type=a['account_type'],asset_class=a['asset_class'],currency=a['currency'],balance=balance,equivalent_balance=amount))
        totals['net_worth']+=amount
        totals['liabilities' if a['account_type']=='liability' else a['asset_class']]+=abs(amount) if a['account_type']=='liability' else amount
        if a['account_type']!='liability' and a['asset_class'] in ('accessible','designated','retirement'):
            buckets[a['currency']]+=balance
    ids={a['id'] for a in accounts}; by_id={a['id']:a for a in accounts}
    # A single SQL aggregation serves dashboard, estimates and all client-side scenarios.
    history=[dict(r) for r in conn.execute('''SELECT t.account_id,t.category_id,t.expense_type,t.income_type,t.spending_class,
        substr(t.tx_date,1,7) month,SUM(CASE WHEN t.amount<0 THEN -t.amount ELSE 0 END) expense,
        SUM(CASE WHEN t.amount>0 THEN t.amount ELSE 0 END) income,COUNT(*) records
        FROM transactions t WHERE t.tx_date>=? AND t.tx_date<? AND COALESCE(t.transfer_group,'')=''
        GROUP BY t.account_id,t.category_id,t.expense_type,t.income_type,t.spending_class,substr(t.tx_date,1,7)''',(str(start),str(end))) if r['account_id'] in ids]
    months=len({r['month'] for r in history}); denominator=max(months,1)
    maturity='mature annual view' if months>=12 else 'established' if months>=6 else 'preliminary' if months>=3 else 'limited history'
    historic=defaultdict(float); historic_income=defaultdict(float); spending=defaultdict(float); unknown=0; excluded=defaultdict(float)
    for row in history:
        a=by_id[row['account_id']]; exp=converted(row['expense'],a['currency'],currency,fx); inc=converted(row['income'],a['currency'],currency,fx)
        if row['expense_type']=='normal':
            historic[(a['id'],row['category_id'])]+=exp/denominator
            spending[row['spending_class']]+=exp/denominator
        else: excluded[row['expense_type']]+=exp
        if row['income_type'] not in ('unclassified',): historic_income[(a['id'],row['income_type'])]+=inc/denominator
        if (exp and row['expense_type']=='unclassified') or (inc and row['income_type']=='unclassified'): unknown+=row['records']
    scheduled=defaultdict(float); historical_schedule=defaultdict(float); scheduled_income=defaultdict(float); historical_income_schedule=defaultdict(float); rules=[]; unknown_rules=0
    for raw in conn.execute('SELECT * FROM recurring_rules WHERE deleted_at IS NULL'):
        r=dict(raw)
        if r['account_id'] not in ids or r['transaction_type']=='transfer': continue
        a=by_id[r['account_id']]; monthly=converted(float(equivalents(r['amount'],r['frequency'])[0]),a['currency'],currency,fx)
        strategy=conn.execute('SELECT end_date FROM funding_strategies WHERE id=?',(r['funding_strategy_id'],)).fetchone() if r['funding_strategy_id'] else None
        ends=min([d for d in (r['end_date'],strategy['end_date'] if strategy else None) if d],default=None)
        effective=bool(r['active'] and r['start_date']<=str(today) and (not ends or ends>=str(today)))
        if r['transaction_type']=='expense' and r['expense_type']=='normal':
            if r['start_date']<str(end) and (not ends or ends>=str(start)):
                historical_schedule[(a['id'],r['category_id'])]+=monthly
            if effective: scheduled[(a['id'],r['category_id'])]+=monthly
        if r['transaction_type']=='income' and r['income_type'] not in ('extraordinary','unclassified') and r['start_date']<str(end) and (not ends or ends>=str(start)):
            historical_income_schedule[(a['id'],r['income_type'])]+=monthly
        if effective and r['transaction_type']=='income' and r['income_type'] not in ('extraordinary','unclassified'):
            scheduled_income[(a['id'],r['income_type'])]+=monthly
            rules.append(dict(key='rule:'+str(r['id']),name=r['description'],account=a['name'],type=r['income_type'],monthly=monthly,basis='Scheduled monthly equivalent'))
        if effective and ((r['transaction_type']=='expense' and r['expense_type']=='unclassified') or (r['transaction_type']=='income' and r['income_type']=='unclassified')): unknown_rules+=1
    residual={key:max(value-historical_schedule.get(key,0),0) for key,value in historic.items()}
    cost=sum(scheduled.values())+sum(residual.values())
    income_sources=rules
    for key,value in historic_income.items():
        additional=max(value-max(scheduled_income.get(key,0),historical_income_schedule.get(key,0)),0)
        if additional:
            income_sources.append(dict(key='history:'+str(key[0])+':'+key[1],name=by_id[key[0]]['name']+' — '+INCOME_TYPES[key[1]],account=by_id[key[0]]['name'],type=key[1],monthly=additional,basis='Observed monthly average; future continuation is an assumption'))
    available=max(totals['accessible']+totals['designated'],0)
    model=dict(normal_monthly_cost=cost,income_sources=income_sources,available_financial_capital=available)
    current=scenario(model)
    exposure=[]; total_eur=sum(converted(v,c,'EUR',fx) for c,v in buckets.items())
    for cur,amount in sorted(buckets.items()):
        eur=converted(amount,cur,'EUR',fx)
        exposure.append(dict(currency=cur,balance=amount,eur_equivalent=eur,percent=eur/total_eur*100 if total_eur else None))
    # Only the GBP leg changes. Other configured currencies retain their current equivalent.
    gbp_eur=converted(buckets.get('GBP',0),'GBP','EUR',fx)
    capital_rows=[dict(r) for r in conn.execute('SELECT * FROM capital_movements WHERE movement_date<=? ORDER BY movement_date,id',(str(today),)) if r['account_id'] in ids]
    capital_start=min((r['movement_date'] for r in capital_rows if r['kind']=='opening'),default=None)
    opening=sum(converted(r['amount'],by_id[r['account_id']]['currency'],currency,fx) for r in capital_rows if r['kind']=='opening')
    movements=sum(converted(r['amount'],by_id[r['account_id']]['currency'],currency,fx) for r in capital_rows if r['kind']=='movement' and capital_start and r['movement_date']>=capital_start)
    capex=extra=0
    if capital_start:
        for row in conn.execute('''SELECT account_id,SUM(CASE WHEN amount<0 AND expense_type='capital' THEN -amount ELSE 0 END) capex,
            SUM(CASE WHEN amount>0 AND income_type='extraordinary' THEN amount ELSE 0 END) extra FROM transactions
            WHERE tx_date>=? AND tx_date<=? AND COALESCE(transfer_group,'')='' GROUP BY account_id''',(capital_start,str(today))):
            if row['account_id'] in ids:
                cur=by_id[row['account_id']]['currency']; capex+=converted(row['capex'],cur,currency,fx); extra+=converted(row['extra'],cur,currency,fx)
    funding=funding_projection(conn,accounts,fx,today)
    retirement_ready=months>=3 and unknown==0 and unknown_rules==0 and all(a['asset_class']!='unclassified' for a in accounts if a['account_type']!='liability')
    return dict(as_of=str(today),currency=currency,accounts=accounts,actual=dict(totals),model=model,operating=current,
        history=dict(start=str(start),end=str(end-timedelta(days=1)),months=months,maturity=maturity,unclassified_records=unknown,unclassified_rules=unknown_rules,
            method='Previous 12 complete calendar months; averages divide by months with recorded activity. Empty months may be missing data. Scheduled normal equivalents plus positive historical residual by account/category avoid double counting. Existing schedules in the history window are deducted from historical category averages, including ended schedules; this conservative estimate may understate variable spending in the same category.'),
        spending_monthly_observed=dict(spending),excluded_expenses_observed=dict(excluded),estimated_additional_monthly_by_account={str(i):sum(v for (aid,_),v in residual.items() if aid==i) for i in ids},
        funding=funding,housing=[f for f in funding if f['kind']=='housing'],
        retirement=dict(ready=retirement_ready,annual_living_cost=cost*12,annual_recurring_income=current['monthly_income']*12,annual_surplus=current['annual_surplus'],
            annual_capital_requirement=current['annual_capital_requirement'],annual_pension_gross_requirement=sum(converted(s['annual_gross'] or 0,s['currency'],currency,fx) for f in funding for s in ([f['current_source']] if f['current_source'] else [])),
            accessible_capital_change_annual=current['annual_surplus'],method='Annualised constant-rate projection, available after three active complete months and classification review. Pension requirements below remain in each funding account currency; no investment returns, inflation or tax forecast. Monitoring, not a safety assessment.'),
        capital=dict(configured=capital_start is not None,start=capital_start,opening=opening,extraordinary_income=extra,capital_expenditure=capex,movements=movements,closing=opening+extra-capex+movements,
            method='Separate capital ledger, not an account balance. Explicit opening entries establish the start date; all classified extraordinary receipts and capital purchases since that date are included. Record other capital movements explicitly, including capital-funded living costs. Do not enter a movement for a receipt or purchase already included.'),
        currency_exposure=dict(gbp_eur_rate=rates_in_eur(fx).get('GBP'),assets=exposure,eur_equivalent=total_eur,gbp_stronger_5=total_eur+gbp_eur*.05,gbp_weaker_5=total_eur-gbp_eur*.05,
            method='Accessible, designated and retirement assets; excludes liabilities, other assets and assets awaiting classification. Illustrative GBP sensitivity, not a prediction.'))
