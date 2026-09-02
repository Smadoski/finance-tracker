"""Repeatable, additive database migrations for Finance Tracker."""


def migrate_v250(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS recurring_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            transaction_type TEXT NOT NULL CHECK(transaction_type IN ('expense','income','transfer')),
            account_id INTEGER NOT NULL REFERENCES accounts(id),
            to_account_id INTEGER REFERENCES accounts(id),
            amount REAL NOT NULL CHECK(amount > 0),
            to_amount REAL,
            category_id INTEGER REFERENCES categories(id),
            start_date TEXT NOT NULL,
            end_date TEXT,
            next_scheduled_date TEXT NOT NULL,
            frequency TEXT NOT NULL CHECK(frequency IN ('daily','weekly','monthly','quarterly','annually')),
            working_day_adjustment TEXT NOT NULL DEFAULT 'exact' CHECK(working_day_adjustment IN ('exact','previous','next')),
            posting_mode TEXT NOT NULL DEFAULT 'automatic' CHECK(posting_mode IN ('automatic','pending')),
            active INTEGER NOT NULL DEFAULT 1,
            deleted_at TEXT,
            created_by INTEGER REFERENCES users(id),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS recurring_occurrences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id INTEGER NOT NULL REFERENCES recurring_rules(id) ON DELETE CASCADE,
            scheduled_date TEXT NOT NULL,
            posting_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('posted','pending','skipped','failed')),
            transaction_id INTEGER REFERENCES transactions(id),
            pending_id INTEGER REFERENCES pending_transactions(id),
            transfer_group TEXT,
            detail TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(rule_id, scheduled_date)
        );
        CREATE INDEX IF NOT EXISTS idx_recurring_due ON recurring_rules(active,next_scheduled_date);
        CREATE INDEX IF NOT EXISTS idx_recurring_history ON recurring_occurrences(rule_id,scheduled_date DESC);

        CREATE TABLE IF NOT EXISTS category_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
            target_amount REAL NOT NULL CHECK(target_amount >= 0),
            currency TEXT NOT NULL CHECK(currency IN ('GBP','EUR')),
            period TEXT NOT NULL CHECK(period IN ('weekly','monthly','quarterly','yearly')),
            active INTEGER NOT NULL DEFAULT 1,
            created_by INTEGER REFERENCES users(id),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(category_id, period)
        );
        CREATE INDEX IF NOT EXISTS idx_category_targets_period ON category_targets(active,period,category_id);
        """
    )
    columns={row[1] for row in conn.execute("PRAGMA table_info(recurring_rules)").fetchall()}
    if 'deleted_at' not in columns:
        conn.execute("ALTER TABLE recurring_rules ADD COLUMN deleted_at TEXT")
    conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('schema_version','2.5.0')")
    conn.execute("UPDATE settings SET value='2.5.0' WHERE key='schema_version'")
    conn.commit()
