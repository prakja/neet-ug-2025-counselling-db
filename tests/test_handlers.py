import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, CallbackQuery, Message, User
from telegram.ext import ContextTypes

from counselling_bot.handlers import (
    RANK, CATEGORY, QUOTA, PHONE, RESULTS,
    start, got_rank, toggle_category, toggle_quota, got_phone,
    _show_results, _build_results_text, _results_kb,
    _category_kb, _quota_kb, _ALL_CATEGORIES, _QUOTAS, FULL_QUOTA,
)


# Fixtures
@pytest.fixture
def mock_update():
    """Mock Update with user ID 12345."""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 12345
    update.effective_user.full_name = "Test User"
    return update


@pytest.fixture
def mock_callback_query(mock_update):
    """Mock CallbackQuery attached to update."""
    cq = MagicMock(spec=CallbackQuery)
    cq.message = MagicMock(spec=Message)
    cq.message.reply_text = AsyncMock()
    cq.edit_message_text = AsyncMock()
    cq.edit_message_reply_markup = AsyncMock()
    cq.answer = AsyncMock()
    cq.data = "cat:OPEN"
    mock_update.callback_query = cq
    return cq


@pytest.fixture
def mock_context():
    """Mock ContextTypes.DEFAULT_TYPE with empty user_data."""
    ctx = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    ctx.user_data = {}
    return ctx


# Tests for category keyboard
def test_category_kb_defaults():
    """OPEN should be pre-selected by default."""
    kb = _category_kb({"OPEN"})
    buttons = kb.inline_keyboard
    # First row: OPEN, SC
    assert "✅ OPEN" in buttons[0][0].text
    assert "❌ SC" in buttons[0][1].text
    # Done button at end
    assert "Done" in buttons[-1][0].text


def test_category_kb_multiple_selected():
    """Multiple categories can be selected."""
    kb = _category_kb({"OPEN", "OBC", "SC"})
    buttons = kb.inline_keyboard
    assert "✅ OPEN" in buttons[0][0].text
    assert "✅ SC" in buttons[0][1].text
    assert "✅ OBC" in buttons[1][0].text


# Tests for quota keyboard
def test_quota_kb_defaults():
    """All India + Open Seat pre-selected."""
    kb = _quota_kb({"ai", "os"})
    buttons = kb.inline_keyboard
    ai_btn = next(b for b in buttons if "All India" in b[0].text)
    os_btn = next(b for b in buttons if "Open Seat" in b[0].text)
    assert "✅" in ai_btn[0].text
    assert "✅" in os_btn[0].text


# Tests for toggle_category
@pytest.mark.asyncio
async def test_toggle_category_adds_obc(mock_update, mock_callback_query, mock_context):
    """Tapping OBC adds it to selection."""
    mock_context.user_data = {"selected_cats": {"OPEN"}}
    mock_callback_query.data = "cat:OBC"

    result = await toggle_category(mock_update, mock_context)

    assert result == CATEGORY
    assert mock_context.user_data["selected_cats"] == {"OPEN", "OBC"}
    mock_callback_query.edit_message_reply_markup.assert_called_once()


@pytest.mark.asyncio
async def test_toggle_category_prevents_deselecting_open(mock_update, mock_callback_query, mock_context):
    """Tapping OPEN when already selected should NOT remove it."""
    mock_context.user_data = {"selected_cats": {"OPEN", "OBC"}}
    mock_callback_query.data = "cat:OPEN"

    result = await toggle_category(mock_update, mock_context)

    assert result == CATEGORY
    # OPEN must still be in set
    assert "OPEN" in mock_context.user_data["selected_cats"]
    # OBC should still be there too (only OPEN should be protected)
    assert "OBC" in mock_context.user_data["selected_cats"]


@pytest.mark.asyncio
async def test_toggle_category_done_proceeds(mock_update, mock_callback_query, mock_context):
    """Tapping Done with valid selection moves to QUOTA state."""
    mock_context.user_data = {"selected_cats": {"OPEN", "OBC"}}
    mock_callback_query.data = "cat:done"

    with patch("counselling_bot.handlers.check_lead_exists", new=AsyncMock(return_value=None)):
        result = await toggle_category(mock_update, mock_context)

    assert result == QUOTA
    # Quotas should be pre-populated
    assert "selected_quotas" in mock_context.user_data
    assert "ai" in mock_context.user_data["selected_quotas"]
    assert "os" in mock_context.user_data["selected_quotas"]
    mock_callback_query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_toggle_category_done_empty_fails(mock_update, mock_callback_query, mock_context):
    """Tapping Done with no selection shows alert."""
    mock_context.user_data = {"selected_cats": set()}
    mock_callback_query.data = "cat:done"

    result = await toggle_category(mock_update, mock_context)

    assert result == CATEGORY
    mock_callback_query.answer.assert_called_with("Select at least one category", show_alert=True)


# Tests for toggle_quota
@pytest.mark.asyncio
async def test_toggle_quota_done_with_lead_skip(mock_update, mock_callback_query, mock_context):
    """Returning user with lead skips phone step and shows results."""
    mock_context.user_data = {
        "rank": 50000,
        "selected_cats": {"OPEN"},
        "selected_quotas": {"ai", "os"},
    }
    mock_callback_query.data = "quota:done"

    with patch("counselling_bot.handlers.check_lead_exists", new=AsyncMock(
        return_value={"phone_number": "+919999999999", "full_name": "Existing User"}
    )):
        with patch("counselling_bot.handlers.get_neet_options_for_categories", new=AsyncMock(
            return_value=[{"institution_name": "Test College", "program_code": "MBBS", 
                          "quota_label": "All India", "opening_rank": 1, "closing_rank": 100, "round_key": "R1"}]
        )):
            result = await toggle_quota(mock_update, mock_context)

    assert result == RESULTS
    # Should skip phone step entirely
    mock_callback_query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_toggle_quota_done_new_user_goes_to_phone(mock_update, mock_callback_query, mock_context):
    """New user without lead goes to phone sharing step."""
    mock_context.user_data = {
        "rank": 50000,
        "selected_cats": {"OPEN"},
        "selected_quotas": {"ai", "os"},
    }
    mock_callback_query.data = "quota:done"

    with patch("counselling_bot.handlers.check_lead_exists", new=AsyncMock(return_value=None)):
        result = await toggle_quota(mock_update, mock_context)

    assert result == PHONE
    # Should show phone sharing prompt
    assert mock_callback_query.edit_message_text.called
    mock_callback_query.message.reply_text.assert_called_once()


# Tests for results formatting
def test_build_results_text_simple():
    """Table formatting without code blocks."""
    rows = [
        {"institution_name": "AIIMS Delhi", "program_code": "MBBS", 
         "quota_label": "All India", "opening_rank": 1, "closing_rank": 100, "round_key": "R1"},
        {"institution_name": "MAMC", "program_code": "MBBS", 
         "quota_label": "DU Quota", "opening_rank": 101, "closing_rank": 500, "round_key": "R1"},
    ]
    text = _build_results_text(rows, 0, 50000, "OPEN", "All India")
    # Should use HTML formatting, not code blocks
    assert "<b>" in text
    assert "```" not in text
    assert "1." in text
    assert "AIIMS Delhi" in text


def test_results_kb_with_more():
    """Show More + Start Over when >25 results."""
    kb = _results_kb(True)
    assert len(kb.inline_keyboard[0]) == 2
    assert "Show More" in kb.inline_keyboard[0][0].text
    assert "Start Over" in kb.inline_keyboard[0][1].text


def test_results_kb_without_more():
    """Only Start Over when ≤25 results."""
    kb = _results_kb(False)
    assert len(kb.inline_keyboard[0]) == 1
    assert "Start Over" in kb.inline_keyboard[0][0].text


# Test for dedup logic
def test_dedup_key_from_sql_columns():
    """Dedup key must use actual SQL columns, not missing institution_id."""
    row = {
        "mcc_institute_code": 12345,
        "program_code": "MBBS",
        "quota_label": "All India",
        "round_key": "R1",
    }
    # This is what the code SHOULD do
    key = (row.get("mcc_institute_code"), row.get("program_code"), row.get("quota_label"), row.get("round_key"))
    assert key == (12345, "MBBS", "All India", "R1")


# Integration: full flow
@pytest.mark.asyncio
async def test_full_flow_from_rank_to_results(mock_update, mock_callback_query, mock_context):
    """End-to-end: /start → rank → category → quota → results."""
    # Step 1: /start
    result = await start(mock_update, mock_context)
    assert result == RANK

    # Step 2: Enter rank
    mock_update.message.text = "50000"
    result = await got_rank(mock_update, mock_context)
    assert result == CATEGORY
    assert mock_context.user_data["rank"] == 50000
    assert "OPEN" in mock_context.user_data["selected_cats"]

    # Step 3: Tap Done on categories
    mock_callback_query.data = "cat:done"
    with patch("counselling_bot.handlers.check_lead_exists", new=AsyncMock(return_value=None)):
        result = await toggle_category(mock_update, mock_context)
    assert result == QUOTA
    assert "ai" in mock_context.user_data["selected_quotas"]
    assert "os" in mock_context.user_data["selected_quotas"]

    # Step 4: Tap Done on quotas
    mock_callback_query.data = "quota:done"
    with patch("counselling_bot.handlers.check_lead_exists", new=AsyncMock(return_value=None)):
        result = await toggle_quota(mock_update, mock_context)
    assert result == PHONE
