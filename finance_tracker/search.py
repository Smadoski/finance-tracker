"""Combined, parameterised transaction search. Amount bounds use native signed amounts."""
from datetime import date
import math


def search_transactions(conn, filters, limit=None, offset=0):
    status=filters.get('status','posted')
    if status not in ('posted','pending','all'): raise ValueError('Choose posted, pending or all.')
    queries=[]; params=[]
    for pending in (False,True):
        if (status=='posted' and pending) or (status=='pending' and not pending): continue
        transfer="NULL" if pending else 't.transfer_group'
        kind=f"CASE WHEN {transfer} IS NOT NULL OR c.kind='transfer' THEN 'transfer' WHEN t.amount<0 THEN 'expense' ELSE 'income' END"
        where=[]; values=[]
        if filters.get('q'):
            where.append("t.description LIKE ? ESCAPE '\\'"); values.append('%'+filters['q'].replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%')
        for key,column in (('account_id','t.account_id'),('subcategory_id','t.category_id'),('user_id','t.created_by')):
            if filters.get(key): where.append(column+'=?'); values.append(int(filters[key]))
        if filters.get('category_id'):
            where.append('(c.id=? OR c.parent_id=?)'); values.extend([int(filters['category_id'])]*2)
        for key,operator in (('start','>='),('end','<=')):
            if filters.get(key): where.append('t.tx_date'+operator+'?'); values.append(date.fromisoformat(filters[key]).isoformat())
        for key,operator in (('min_amount','>='),('max_amount','<=')):
            if filters.get(key):
                value=float(filters[key])
                if not math.isfinite(value): raise ValueError('Amount must be finite.')
                where.append('t.amount'+operator+'?'); values.append(value)
        if filters.get('type'):
            if filters['type'] not in ('income','expense','transfer'): raise ValueError('Invalid transaction type.')
            where.append(kind+'=?'); values.append(filters['type'])
        table='pending_transactions' if pending else 'transactions'
        queries.append(f'''SELECT t.id,t.tx_date,t.description,t.amount,t.account_id,t.category_id,a.name account,a.currency,
            COALESCE(p.name,c.name,'Uncategorised') category,CASE WHEN p.id IS NOT NULL THEN c.name ELSE '' END subcategory,
            COALESCE(u.name,'') paid_by,{kind} type, '{'pending' if pending else 'posted'}' status
            FROM {table} t JOIN accounts a ON a.id=t.account_id LEFT JOIN categories c ON c.id=t.category_id
            LEFT JOIN categories p ON p.id=c.parent_id LEFT JOIN users u ON u.id=t.created_by
            {'WHERE '+ ' AND '.join(where) if where else ''}''')
        params.extend(values)
    sql='SELECT * FROM ('+' UNION ALL '.join(queries)+') ORDER BY tx_date DESC,id DESC'
    if limit is not None: sql+=' LIMIT ? OFFSET ?'; params.extend([limit,offset])
    return [dict(r) for r in conn.execute(sql,params)]
