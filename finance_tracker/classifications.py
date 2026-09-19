"""Independent, explicit classifications; never inferred from amount or category."""
ASSET_CLASSES = {'unclassified':'Needs review', 'accessible':'Accessible financial assets', 'retirement':'Pension / retirement', 'other':'Other assets', 'designated':'Designated / ring-fenced capital'}
EXPENSE_TYPES = {'unclassified':'Needs review', 'normal':'Normal / living expense', 'capital':'Capital expenditure', 'exceptional':'Exceptional / one-off'}
INCOME_TYPES = {'unclassified':'Needs review', 'salary':'Salary', 'state_pension':'State pension', 'private_pension':'Private pension', 'investment':'Savings / investment income', 'other_recurring':'Other recurring income', 'extraordinary':'Extraordinary income'}
SPENDING_CLASSES = {'unclassified':'Needs review', 'essential':'Essential', 'lifestyle':'Lifestyle / discretionary'}
FIELDS = ('expense_type','income_type','spending_class','funding_source_id','funding_strategy_id')
TABLES = ('transactions','pending_transactions','recurring_rules')


def save_classification(conn, table, row_id, data):
    if table not in TABLES: raise ValueError('Invalid classification record.')
    row = conn.execute(f'SELECT * FROM {table} WHERE id=?',(row_id,)).fetchone()
    if not row: raise ValueError('Record no longer exists.')
    values = dict(row)
    for key, choices in [('expense_type',EXPENSE_TYPES),('income_type',INCOME_TYPES),('spending_class',SPENDING_CLASSES)]:
        if key in data:
            if data[key] not in choices: raise ValueError('Invalid classification.')
            values[key] = data[key]
    for key, target in [('funding_source_id','funding_sources'),('funding_strategy_id','funding_strategies')]:
        if key in data:
            values[key] = int(data[key]) if data[key] else None
            if values[key] and not conn.execute(f'SELECT id FROM {target} WHERE id=?',(values[key],)).fetchone():
                raise ValueError('Funding selection no longer exists.')
    conn.execute(f'UPDATE {table} SET '+','.join(f'{key}=?' for key in FIELDS)+' WHERE id=?', [values[key] for key in FIELDS]+[row_id])


def copy_classification(conn, source, target, row_id):
    if target not in TABLES: raise ValueError('Invalid classification record.')
    if not all(key in source.keys() for key in FIELDS): return
    conn.execute(f'UPDATE {target} SET '+','.join(f'{key}=?' for key in FIELDS)+' WHERE id=?', [source[key] for key in FIELDS]+[row_id])
