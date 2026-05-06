-- Fix sequence permissions for neet_bot_user (needed for SERIAL columns in INSERT)
BEGIN;

-- Grant usage on all existing sequences
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA neetcounselling2025 TO neet_bot_user;

-- Set default privileges so future sequences also get grants
ALTER DEFAULT PRIVILEGES IN SCHEMA neetcounselling2025
    GRANT USAGE, SELECT ON SEQUENCES TO neet_bot_user;

COMMIT;
