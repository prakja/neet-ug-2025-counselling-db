import logging
import json
import asyncpg
from .config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT

logger = logging.getLogger(__name__)
_pool = None


async def get_pool():
    global _pool
    if _pool is None or _pool._closed or not _pool._initialized:
        _pool = await asyncpg.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            min_size=1,
            max_size=5,
            command_timeout=30,
        )
        logger.info("DB pool created for %s@%s/%s", DB_USER, DB_HOST, DB_NAME)
    return _pool


async def get_neet_options_for_categories(rank, categories: list, quotas: list, max_rows=30):
    pool = await get_pool()
    quota_arr = quotas if quotas else None
    seen = set()
    all_rows = []

    async with pool.acquire() as conn:
        for cat in categories:
            rows = await conn.fetch(
                "SELECT * FROM neetcounselling2025.fn_available_options_by_rank($1, $2, false, null, null, true, $3, $4)",
                rank, cat, quota_arr, max_rows,
            )
            for r in rows:
                key = (r.get("institution_id"), r.get("program_code"), r.get("quota_label"), r.get("round_key"))
                if key not in seen:
                    seen.add(key)
                    all_rows.append(dict(r))
    # Sort by closing_rank ascending for best options first
    all_rows.sort(key=lambda r: (r.get("closing_rank") or 9999999))
    return all_rows


async def get_neet_options(rank, category="OPEN", quota=None, max_rows=30):
    pool = await get_pool()
    quota_arr = [quota] if quota else None
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM neetcounselling2025.fn_available_options_by_rank($1, $2, false, null, null, true, $3, $4)",
            rank, category, quota_arr, max_rows,
        )
    return [dict(r) for r in rows]


async def store_lead(telegram_user_id, phone, full_name, rank, categories, quotas):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO neetcounselling2025.leads
                (telegram_user_id, phone_number, full_name, rank, categories, quotas)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT DO NOTHING
            """,
            telegram_user_id,
            phone,
            full_name,
            rank,
            json.dumps(categories),
            json.dumps(quotas),
        )
    logger.info("Stored lead for user %s rank %s", telegram_user_id, rank)


async def get_quota_labels():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT DISTINCT quota_label FROM neetcounselling2025.quota ORDER BY quota_label")
    return [r["quota_label"] for r in rows]


async def close_pool(app=None):
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("DB pool closed")
