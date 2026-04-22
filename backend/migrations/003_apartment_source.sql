ALTER TABLE apartments ADD COLUMN source TEXT;
ALTER TABLE apartments ADD COLUMN source_url TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS apartments_source_url_uniq
    ON apartments(source_url) WHERE source_url IS NOT NULL;
