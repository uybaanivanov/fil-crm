CREATE TABLE IF NOT EXISTS currency_rates (
    date TEXT NOT NULL,
    code TEXT NOT NULL,
    rate_to_rub REAL NOT NULL,
    PRIMARY KEY (date, code)
);
