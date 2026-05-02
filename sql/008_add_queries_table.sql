BEGIN;

DELETE FROM neetcounselling2025.leads a
WHERE a.id NOT IN (
    SELECT MAX(id) FROM neetcounselling2025.leads b WHERE b.telegram_user_id = a.telegram_user_id
);

ALTER TABLE neetcounselling2025.leads
    ADD CONSTRAINT leads_telegram_user_id_key UNIQUE (telegram_user_id);

CREATE TABLE IF NOT EXISTS neetcounselling2025.queries (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT NOT NULL,
    rank INTEGER NOT NULL,
    categories JSONB DEFAULT '[]'::jsonb,
    quotas JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_queries_user_id ON neetcounselling2025.queries(telegram_user_id);

COMMIT;
