-- 006_apartment_expenses.sql

ALTER TABLE apartments ADD COLUMN monthly_rent INTEGER;
ALTER TABLE apartments ADD COLUMN monthly_utilities INTEGER;

ALTER TABLE expenses ADD COLUMN apartment_id INTEGER REFERENCES apartments(id);
ALTER TABLE expenses ADD COLUMN source TEXT NOT NULL DEFAULT 'manual'
    CHECK (source IN ('manual', 'auto'));

CREATE INDEX idx_expenses_apartment ON expenses(apartment_id);

-- Идемпотентность авто-генерации: одна запись rent/utilities на квартиру в месяц
CREATE UNIQUE INDEX idx_expenses_auto_unique
    ON expenses(apartment_id, category, substr(occurred_at, 1, 7))
    WHERE source = 'auto';
