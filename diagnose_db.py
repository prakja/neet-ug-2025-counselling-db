"""One-off DB diagnostic script. Run in ECS to check prod state."""
import asyncio
import json
import asyncpg
from counselling_bot.config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT


async def diagnose():
    conn = await asyncpg.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    print("Connected OK")

    tables = await conn.fetch(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'neetcounselling2025'
        ORDER BY table_name
        """
    )
    print(f"Schema tables: {[r['table_name'] for r in tables]}")

    has_leads = any(r["table_name"] == "leads" for r in tables)
    has_queries = any(r["table_name"] == "queries" for r in tables)

    if has_leads:
        count = await conn.fetchval("SELECT COUNT(*) FROM neetcounselling2025.leads")
        print(f"leads rows: {count}")
    else:
        print("MISSING: leads table")

    if has_queries:
        count = await conn.fetchval("SELECT COUNT(*) FROM neetcounselling2025.queries")
        print(f"queries rows: {count}")
    else:
        print("MISSING: queries table")

    funcs = await conn.fetch(
        """
        SELECT routine_name
        FROM information_schema.routines
        WHERE routine_schema = 'neetcounselling2025'
          AND routine_name = 'fn_available_options_by_rank'
        """
    )
    if funcs:
        print("fn_available_options_by_rank: EXISTS")
    else:
        print("MISSING: fn_available_options_by_rank")

    inst = await conn.fetchval("SELECT COUNT(*) FROM neetcounselling2025.institution")
    print(f"institution rows: {inst}")

    rc = await conn.fetchval("SELECT COUNT(*) FROM neetcounselling2025.round_cutoff")
    print(f"round_cutoff rows: {rc}")

    await conn.close()
    print("Done")


if __name__ == "__main__":
    asyncio.run(diagnose())
