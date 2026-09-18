"""Reviewable CSV ingestion; independent of Flask and ready for other ingestion adapters."""
import csv
import io
import math
from datetime import datetime
from .money import convert

FIELDS=('date','description','amount','debit','credit','currency','category')


def csv_text(headers, rows):
    output=io.StringIO(newline=''); writer=csv.writer(output); writer.writerow(headers)
    for row in rows:
        writer.writerow([("'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@','\t','\r')) else v) for v in row])
    return '\ufeff'+output.getvalue()


def export_transactions(rows, currency, fx):
    return csv_text(['Date','Description','Account','Category','Subcategory','Type','Amount','Currency','Equivalent value','Equivalent currency','Paid by','Status'],
        ([r['tx_date'],r['description'],r['account'],r['category'],r['subcategory'],r['type'],r['amount'],r['currency'],convert(r['amount'],r['currency'],currency,fx),currency,r['paid_by'],r['status']] for r in rows))


def parse_csv(content):
    if len(content)>2*1024*1024: raise ValueError('CSV limit is 2 MB.')
    try: text=content.decode('utf-8-sig')
    except UnicodeDecodeError: raise ValueError('Use a UTF-8 CSV file.')
    reader=csv.reader(io.StringIO(text),strict=True)
    try:
        headers=next(reader)
        if not headers or len(headers)>100 or len(set(headers))!=len(headers): raise ValueError('CSV needs unique column headings (maximum 100).')
        rows=[]
        for row in reader:
            if not any(row): continue
            if len(rows)>=5000: raise ValueError('Import at most 5,000 rows at a time.')
            rows.append(row)
        if not rows: raise ValueError('CSV has no transaction rows.')
    except (csv.Error,StopIteration) as exc: raise ValueError('Invalid CSV file.') from exc
    return dict(headers=headers,rows=rows)


def preview_import(conn, source, mapping, account_id, date_format='%Y-%m-%d'):
    account=conn.execute("SELECT * FROM accounts WHERE id=? AND active=1 AND account_type NOT IN ('pension','other_asset','liability')",(account_id,)).fetchone()
    if not account: raise ValueError('Choose an active transaction account.')
    if not mapping.get('date') or not mapping.get('description') or not (mapping.get('amount') or mapping.get('debit') or mapping.get('credit')): raise ValueError('Map date, description and amount (or debit/credit).')
    if date_format not in ('%Y-%m-%d','%d/%m/%Y','%m/%d/%Y'): raise ValueError('Invalid date format.')
    for column in mapping.values():
        if column and column not in source['headers']: raise ValueError('Unknown mapped column.')
    seen={(r['tx_date'],round(r['amount'],8),r['description'].strip().casefold()) for r in conn.execute('SELECT tx_date,amount,description FROM transactions WHERE account_id=?',(account_id,))}
    seen.update((r['tx_date'],round(r['amount'],8),r['description'].strip().casefold()) for r in conn.execute('SELECT tx_date,amount,description FROM pending_transactions WHERE account_id=?',(account_id,)))
    result=[]
    for number,raw in enumerate(source['rows'],1):
        row=dict(number=number,error=None,duplicate=False)
        try:
            if len(raw)!=len(source['headers']): raise ValueError('Column count differs from heading row.')
            data=dict(zip(source['headers'],raw))
            def value(field): return data.get(mapping.get(field),'').strip()
            def money(text):
                number=float(text.replace(',','') or '0')
                if not math.isfinite(number): raise ValueError('Amount must be finite.')
                return number
            day=datetime.strptime(value('date'),date_format).date().isoformat()
            amount=money(value('amount')) if mapping.get('amount') else abs(money(value('credit')))-abs(money(value('debit')))
            if not amount: raise ValueError('Amount must not be zero.')
            description=value('description')
            if not description: raise ValueError('Description is required.')
            if value('currency') and value('currency').upper()!=account['currency']: raise ValueError('Currency must match destination account; convert before importing.')
            category_id=None; category=value('category')
            if category:
                match=conn.execute('SELECT id,kind FROM categories WHERE name=? COLLATE NOCASE',(category,)).fetchone()
                if not match or match['kind']!=('expense' if amount<0 else 'income'): raise ValueError('Unknown category or category does not match amount sign. Map or ignore this column.')
                category_id=match['id']
            key=(day,round(amount,8),description.casefold())
            row.update(tx_date=day,description=description,amount=amount,currency=account['currency'],category=category,category_id=category_id,account_id=int(account_id),duplicate=key in seen)
            seen.add(key)
        except (ValueError,TypeError,OverflowError) as exc: row['error']=str(exc)
        result.append(row)
    return result


def import_reviewed(conn, rows, selected, allow_duplicates, user_id):
    summary=dict(imported=0,skipped=0,duplicates=sum(bool(r['duplicate']) for r in rows),failed=0)
    for row in rows:
        if row['error']: summary['failed']+=1; continue
        if str(row['number']) not in selected or (row['duplicate'] and str(row['number']) not in allow_duplicates): summary['skipped']+=1; continue
        conn.execute('INSERT INTO transactions(account_id,tx_date,description,amount,category_id,created_by) VALUES(?,?,?,?,?,?)',
            (row['account_id'],row['tx_date'],row['description'],row['amount'],row['category_id'],user_id))
        summary['imported']+=1
    return summary
