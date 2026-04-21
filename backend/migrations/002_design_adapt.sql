-- Расширение apartments: декоративные/классификационные поля
ALTER TABLE apartments ADD COLUMN cover_url TEXT;
ALTER TABLE apartments ADD COLUMN rooms TEXT;
ALTER TABLE apartments ADD COLUMN area_m2 INTEGER;
ALTER TABLE apartments ADD COLUMN floor TEXT;
ALTER TABLE apartments ADD COLUMN district TEXT;

-- Расходы — отдельная сущность для /finance
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount INTEGER NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    occurred_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_expenses_occurred ON expenses(occurred_at);
