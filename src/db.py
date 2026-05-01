import logging
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


async def get_neet_options(rank, category="OPEN", quota=None, max_rows=30):
    pool = await get_pool()
    quota_arr = [quota] if quota else None
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM neetcounselling2025.fn_available_options_by_rank($1, $2, false, null, null, true, $3, $4)",
            rank, category, quota_arr, max_rows,
        )
    return [dict(r) for r in rows]


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
