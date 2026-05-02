import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from counselling_bot.db import (
    get_neet_options,
    get_neet_options_for_categories,
    store_lead,
    check_lead_exists,
)


# This test verifies the SQL function signature is correct
@pytest.mark.asyncio
async def test_sql_params_all_eight_present():
    """
    The SQL function fn_available_options_by_rank has 8 parameters.
    This test verifies we pass all 8 in correct order.
    
    If any param is missing or out of order, the function will:
    - Return wrong results (quota_arr in p_is_pwd boolean slot)
    - Or crash with type mismatch
    """
    with patch("counselling_bot.db.get_pool") as mock_pool:
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_pool.return_value.acquire = MagicMock()
        mock_pool.return_value.acquire.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.return_value.acquire.__aexit__ = AsyncMock(return_value=False)
        
        await get_neet_options(rank=50000, category="OPEN", quota="All India", max_rows=10)
        
        call_args = mock_conn.fetch.call_args
        sql = call_args[0][0]
        params = call_args[0][1:]
        
        # Verify SQL has 8 params
        assert "$8" in sql, "SQL must reference $8 (8 parameters)"
        
        # Verify parameter types/order
        assert params[0] == 50000       # $1 rank (int)
        assert params[1] == "OPEN"        # $2 category (text)
        assert params[2] == False         # $3 is_pwd (bool)
        assert params[3] is None        # $4 program_codes (null)
        assert params[4] is None        # $5 round_keys (null)
        assert params[5] == True        # $6 include_after_stray (bool)
        assert params[6] == ["All India"]  # $7 quota_labels (text[])
        assert params[7] == 10          # $8 max_rows (int)


@pytest.mark.asyncio
async def test_multi_category_queries():
    """When multiple categories selected, query each and dedup."""
    row_open = {
        "mcc_institute_code": 1001, "program_code": "MBBS",
        "quota_label": "All India", "round_key": "R1",
        "institution_name": "AIIMS Delhi", "closing_rank": 100,
    }
    row_obc = {
        "mcc_institute_code": 1001, "program_code": "MBBS",  # same college, different category
        "quota_label": "All India", "round_key": "R1",
        "institution_name": "AIIMS Delhi", "closing_rank": 200,
    }
    
    with patch("counselling_bot.db.get_pool") as mock_pool:
        mock_conn = AsyncMock()
        # First call (OPEN) returns 2 rows
        # Second call (OBC) returns 1 row, but one is duplicate
        mock_conn.fetch = AsyncMock(side_effect=[
            [row_open, row_open],  # OPEN query
            [row_obc],             # OBC query (same key as first)
        ])
        mock_pool.return_value.acquire = MagicMock()
        mock_pool.return_value.acquire.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.return_value.acquire.__aexit__ = AsyncMock(return_value=False)
        
        results = await get_neet_options_for_categories(
            rank=50000, categories=["OPEN", "OBC"], quotas=["All India"], max_rows=100
        )
        
        # Should dedup: OPEN gives 2, OBC gives 1 duplicate → total 2 unique
        assert len(results) == 2
        # Should be sorted by closing_rank
        assert results[0]["closing_rank"] <= results[1]["closing_rank"]


@pytest.mark.asyncio
async def test_store_and_check_lead():
    """Store lead then verify it exists."""
    with patch("counselling_bot.db.get_pool") as mock_pool:
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            "phone_number": "+919999999999",
            "full_name": "Test User",
        })
        mock_pool.return_value.acquire = MagicMock()
        mock_pool.return_value.acquire.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.return_value.acquire.__aexit__ = AsyncMock(return_value=False)
        
        await store_lead(
            telegram_user_id=12345,
            phone="+919999999999",
            full_name="Test User",
            rank=50000,
            categories=["OPEN"],
            quotas=["All India"],
        )
        
        existing = await check_lead_exists(12345)
        
        assert existing is not None
        assert existing["phone_number"] == "+919999999999"
        assert existing["full_name"] == "Test User"
