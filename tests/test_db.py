import pytest
from unittest.mock import AsyncMock, patch

from counselling_bot.db import (
    get_neet_options,
    get_neet_options_for_categories,
    store_lead,
    check_lead_exists,
)


class FakeConn:
    def __init__(self, fetch_return=None, fetch_side_effect=None, fetchrow_return=None):
        if fetch_side_effect is not None:
            self.fetch = AsyncMock(side_effect=fetch_side_effect)
        else:
            self.fetch = AsyncMock(return_value=fetch_return)
        self.execute = AsyncMock()
        self.fetchrow = AsyncMock(return_value=fetchrow_return)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class FakePool:
    def __init__(self, fetch_return=None, fetch_side_effect=None, fetchrow_return=None):
        self._conn = FakeConn(fetch_return, fetch_side_effect, fetchrow_return)

    def acquire(self):
        return self._conn


@pytest.mark.asyncio
async def test_sql_params_all_eight_present():
    pool = FakePool(fetch_return=[])
    with patch("counselling_bot.db.get_pool", new=AsyncMock(return_value=pool)):
        await get_neet_options(rank=50000, category="OPEN", quota="All India", max_rows=10)

    pool._conn.fetch.assert_called_once()
    call_args = pool._conn.fetch.call_args
    sql = call_args[0][0]
    params = call_args[0][1:]

    assert "$8" in sql
    assert params[0] == 50000
    assert params[1] == "OPEN"
    assert params[2] == False
    assert params[3] is None
    assert params[4] is None
    assert params[5] == True
    assert params[6] == ["All India"]
    assert params[7] == 10


@pytest.mark.asyncio
async def test_multi_category_queries():
    row_open_1 = {
        "mcc_institute_code": 1001, "program_code": "MBBS",
        "quota_label": "All India", "round_key": "R1",
        "institution_name": "AIIMS Delhi", "closing_rank": 100,
    }
    row_open_2 = {
        "mcc_institute_code": 1002, "program_code": "MBBS",
        "quota_label": "All India", "round_key": "R1",
        "institution_name": "MAMC", "closing_rank": 150,
    }
    row_obc_dup = {
        "mcc_institute_code": 1001, "program_code": "MBBS",
        "quota_label": "All India", "round_key": "R1",
        "institution_name": "AIIMS Delhi", "closing_rank": 200,
    }

    pool = FakePool(
        fetch_side_effect=[
            [row_open_1, row_open_2],
            [row_obc_dup],
        ]
    )
    with patch("counselling_bot.db.get_pool", new=AsyncMock(return_value=pool)):
        results = await get_neet_options_for_categories(
            rank=50000, categories=["OPEN", "OBC"], quotas=["All India"], max_rows=100
        )

    assert len(results) == 2
    assert results[0]["closing_rank"] <= results[1]["closing_rank"]


@pytest.mark.asyncio
async def test_store_and_check_lead():
    pool = FakePool(fetchrow_return={"phone_number": "+919999999999", "full_name": "Test User"})
    with patch("counselling_bot.db.get_pool", new=AsyncMock(return_value=pool)):
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
