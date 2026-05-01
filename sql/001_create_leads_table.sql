CREATE TABLE IF NOT EXISTS neetcounselling2025.leads (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT,
    phone_number TEXT NOT NULL,
    full_name TEXT,
    rank INTEGER NOT NULL,
    categories JSONB DEFAULT '[]'::jsonb,
    quotas JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE neetcounselling2025.leads IS 'Prospective student leads captured via Telegram bot';
COMMENT ON COLUMN neetcounselling2025.leads.phone_number IS 'Phone number shared by user via Telegram contact';
COMMENT ON COLUMN neetcounselling2025.leads.rank IS 'NEET All India Rank';
COMMENT ON COLUMN neetcounselling2025.leads.categories IS 'JSON array of selected candidate categories e.g. ["OPEN", "OBC"]';
COMMENT ON COLUMN neetcounselling2025.leads.quotas IS 'JSON array of selected quota types e.g. ["All India", "DU Quota"]';
