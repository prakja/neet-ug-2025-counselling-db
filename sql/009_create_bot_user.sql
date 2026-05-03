-- Create a dedicated read-write user for the NEET counselling bot
-- with access limited to the neetcounselling2025 schema only

DO $$
DECLARE
    new_user TEXT := 'neet_bot_user';
    new_pass TEXT := 'XUzclbAOA5ALQpY6';
BEGIN
    -- Create role if not exists
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = new_user) THEN
        EXECUTE format('CREATE ROLE %I WITH LOGIN PASSWORD %L', new_user, new_pass);
    ELSE
        EXECUTE format('ALTER ROLE %I WITH PASSWORD %L', new_user, new_pass);
    END IF;
END $$;

-- Grant schema usage
GRANT USAGE ON SCHEMA neetcounselling2025 TO neet_bot_user;

-- Grant read-write on all existing tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA neetcounselling2025 TO neet_bot_user;

-- Grant execute on all existing functions (needed for fn_available_options_by_rank)
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA neetcounselling2025 TO neet_bot_user;

-- Set default privileges so future objects also get grants
ALTER DEFAULT PRIVILEGES IN SCHEMA neetcounselling2025
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO neet_bot_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA neetcounselling2025
    GRANT EXECUTE ON FUNCTIONS TO neet_bot_user;

-- Verify
SELECT
    grantee,
    table_schema,
    table_name,
    privilege_type
FROM information_schema.table_privileges
WHERE grantee = 'neet_bot_user'
  AND table_schema = 'neetcounselling2025'
ORDER BY table_name, privilege_type;
