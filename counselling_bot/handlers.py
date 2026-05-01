"""Telegram bot handlers for NEET rank to college lookup.

Conversation flow: /start → rank → category → quota → results
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from .db import get_neet_options, close_pool

logger = logging.getLogger(__name__)

RANK, CATEGORY, QUOTA, RESULTS = range(4)
CATEGORIES = ["OPEN", "SC", "ST", "OBC", "EWS"]

QUOTAS = [
    "All India",
    "Open Seat Quota",
    "Delhi University Quota",
    "Deemed/Paid Seats Quota",
    "Aligarh Muslim University (AMU) Quota",
    "Non-Resident Indian",
    "Internal - Puducherry UT Domicile",
    "Delhi NCR Children/Widows of Personnel of the Armed Forces (CW) DU Quota",
    "Employees State Insurance Scheme(ESI)",
    "Jamia Internal Quota",
]

QUOTA_SHORT = {
    "All India": "All India",
    "Open Seat Quota": "Open Seat",
    "Delhi University Quota": "DU Quota",
    "Deemed/Paid Seats Quota": "Deemed/Paid",
    "Aligarh Muslim University (AMU) Quota": "AMU Quota",
    "Non-Resident Indian": "NRI",
    "Internal - Puducherry UT Domicile": "Puducherry",
    "Delhi NCR Children/Widows of Personnel of the Armed Forces (CW) DU Quota": "CW DU",
    "Employees State Insurance Scheme(ESI)": "ESI",
    "Jamia Internal Quota": "Jamia",
}

# Short codes must stay under Telegram's 64-byte callback_data limit
QUOTA_CODES = {
    "All India": "ai",
    "Open Seat Quota": "os",
    "Delhi University Quota": "du",
    "Deemed/Paid Seats Quota": "dp",
    "Aligarh Muslim University (AMU) Quota": "am",
    "Non-Resident Indian": "nr",
    "Internal - Puducherry UT Domicile": "pu",
    "Delhi NCR Children/Widows of Personnel of the Armed Forces (CW) DU Quota": "cw",
    "Employees State Insurance Scheme(ESI)": "es",
    "Jamia Internal Quota": "ja",
}
FULL_QUOTA = {v: k for k, v in QUOTA_CODES.items()}


def _kb(items, prefix):
    buttons = [InlineKeyboardButton(l, callback_data=f"{prefix}:{v}")
               for v, l in items]
    return InlineKeyboardMarkup([buttons[i:i + 2] for i in range(0, len(buttons), 2)])


async def start(u: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    await u.message.reply_text(
        "<b>NEET College Predictor</b>\n\n"
        "Send your <b>NEET All India Rank</b> (e.g. <code>27360</code>):",
        parse_mode=ParseMode.HTML,
    )
    return RANK


async def got_rank(u: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    text = u.message.text.strip()
    if not text.isdigit():
        await u.message.reply_text("Enter a valid number rank.")
        return RANK
    ctx.user_data["rank"] = int(text)
    await u.message.reply_text(
        "Pick your <b>category</b>:",
        reply_markup=_kb([(c, c) for c in CATEGORIES], "cat"),
        parse_mode=ParseMode.HTML,
    )
    return CATEGORY


async def got_category(u: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = u.callback_query
    await q.answer()
    _, cat = q.data.split(":", 1)
    ctx.user_data["category"] = cat
    items = [(QUOTA_CODES[v], QUOTA_SHORT.get(v, v)) for v in QUOTAS]
    items.append(("*", "All Quotas"))
    await q.edit_message_text(
        f"Category: <b>{cat}</b>\n\nPick <b>quota</b>:",
        reply_markup=_kb(items, "quota"),
        parse_mode=ParseMode.HTML,
    )
    return QUOTA


def _format_row(idx: int, row: dict) -> str:
    name = row.get("institution_name", "?")
    prog = row.get("program_code", "")
    ql = row.get("quota_label", "")
    o = row.get("opening_rank", "")
    c = row.get("closing_rank", "")
    rnd = row.get("round_key", "")
    return (
        f"<b>{idx}. {name}</b>\n"
        f"   Program: {prog} | Quota: {ql}\n"
        f"   Rank: {o} → {c} | Round: {rnd}\n"
    )


def _results_kb(has_more: bool) -> InlineKeyboardMarkup:
    buttons = []
    if has_more:
        buttons.append(InlineKeyboardButton("📋 Show More", callback_data="more"))
    buttons.append(InlineKeyboardButton("🔄 Start Over", callback_data="restart"))
    return InlineKeyboardMarkup([buttons])


def _build_results_text(rows: list, offset: int, rank: int, cat: str, quota_label: str) -> str:
    total = len(rows)
    end = min(offset + 25, total)
    header = f"<b>Results for Rank {rank} ({cat}) | Quota: {quota_label}</b>\n"
    header += f"<i>Showing {offset + 1}-{end} of {total} colleges</i>\n\n"
    lines = [_format_row(i + 1, row) for i, row in enumerate(rows[offset:end], start=offset)]
    text = header + "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n… <i>(truncated)</i>"
    return text


async def got_quota(u: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = u.callback_query
    await q.answer()
    _, quota_code = q.data.split(":", 1)

    rank = ctx.user_data["rank"]
    cat = ctx.user_data["category"]
    quota = None if quota_code == "*" else FULL_QUOTA.get(quota_code, quota_code)
    quota_label = "All Quotas" if quota is None else quota

    try:
        rows = await get_neet_options(rank, cat, quota, max_rows=100)
    except Exception as e:
        logger.error("DB error: %s", e)
        await q.edit_message_text("Could not fetch results. Try again later.")
        return ConversationHandler.END

    if not rows:
        await q.edit_message_text(
            f"No colleges found for Rank <b>{rank}</b>, Category <b>{cat}</b>.",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END

    ctx.user_data["results"] = rows
    ctx.user_data["results_offset"] = 0
    ctx.user_data["quota_label"] = quota_label

    text = _build_results_text(rows, 0, rank, cat, quota_label)
    has_more = len(rows) > 25
    await q.edit_message_text(text, reply_markup=_results_kb(has_more), parse_mode=ParseMode.HTML)
    return RESULTS


async def show_more(u: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = u.callback_query
    await q.answer()

    rows = ctx.user_data.get("results", [])
    offset = ctx.user_data.get("results_offset", 0) + 25
    ctx.user_data["results_offset"] = offset

    rank = ctx.user_data["rank"]
    cat = ctx.user_data["category"]
    quota_label = ctx.user_data.get("quota_label", "")

    text = _build_results_text(rows, offset, rank, cat, quota_label)
    has_more = len(rows) > offset + 25
    await q.edit_message_text(text, reply_markup=_results_kb(has_more), parse_mode=ParseMode.HTML)
    return RESULTS


async def start_over(u: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = u.callback_query
    await q.answer()
    ctx.user_data.clear()
    await q.edit_message_text(
        "<b>NEET College Predictor</b>\n\nSend your <b>NEET All India Rank</b> (e.g. <code>27360</code>):",
        parse_mode=ParseMode.HTML,
    )
    return RANK


async def cancel(u: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    await u.message.reply_text("Cancelled. /start to restart.")
    return ConversationHandler.END


async def help_cmd(u: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await u.message.reply_text(
        "<b>How to use</b>\n"
        "1. /start\n"
        "2. Enter your NEET All India Rank\n"
        "3. Pick category (OPEN, SC, ST, OBC, EWS)\n"
        "4. Pick quota type (All India, Open Seat, DU, etc.)\n"
        "5. See available colleges\n\n"
        "/start to restart.",
        parse_mode=ParseMode.HTML,
    )


async def error_handler(update: Update | None, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Telegram error: %s", ctx.error, exc_info=ctx.error)
    if update and update.message:
        await update.message.reply_text("Something went wrong. /start to try again.")


def create_app(token: str) -> Application:
    app = (
        Application.builder()
        .token(token)
        .post_shutdown(close_pool)
        .build()
    )

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            RANK: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_rank)],
            CATEGORY: [CallbackQueryHandler(got_category, pattern=r"^cat:")],
            QUOTA: [CallbackQueryHandler(got_quota, pattern=r"^quota:")],
            RESULTS: [
                CallbackQueryHandler(show_more, pattern=r"^more$"),
                CallbackQueryHandler(start_over, pattern=r"^restart$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_error_handler(error_handler)
    return app
