"""Telegram bot handlers for NEET rank to college lookup.

Conversation flow:
/start → rank → multi-select category → done → multi-select quota → done → phone → results
"""
import html
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
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

from .db import get_neet_options, get_neet_options_for_categories, store_lead, check_lead_exists, close_pool

logger = logging.getLogger(__name__)

RANK, CATEGORY, QUOTA, PHONE, RESULTS = range(5)
_ALL_CATEGORIES = ["OPEN", "SC", "ST", "OBC", "EWS"]
_QUOTAS = [
    ("All India", "ai"),
    ("Open Seat Quota", "os"),
    ("Delhi University Quota", "du"),
    ("Deemed/Paid Seats Quota", "dp"),
    ("Aligarh Muslim University (AMU) Quota", "am"),
    ("Non-Resident Indian", "nr"),
    ("Internal – Puducherry UT Domicile", "pu"),
    ("Delhi NCR Children/Widows of Personnel of the Armed Forces (CW) DU Quota", "cw"),
    ("Employees State Insurance Scheme(ESI)", "es"),
    ("Jamia Internal Quota", "ja"),
]
FULL_QUOTA = {code: name for name, code in _QUOTAS}


def _category_kb(selected: set) -> InlineKeyboardMarkup:
    buttons = []
    for cat in _ALL_CATEGORIES:
        mark = "✅" if cat in selected else "❌"
        buttons.append(InlineKeyboardButton(f"{mark} {cat}", callback_data=f"cat:{cat}"))
    done_btn = InlineKeyboardButton("✅ Done", callback_data="cat:done")
    return InlineKeyboardMarkup([buttons[i:i + 2] for i in range(0, len(buttons), 2)] + [[done_btn]])


def _quota_kb(selected: set) -> InlineKeyboardMarkup:
    buttons = []
    for name, code in _QUOTAS:
        mark = "✅" if code in selected else "❌"
        short = name.split("(")[0].strip()[:20]
        buttons.append(InlineKeyboardButton(f"{mark} {short}", callback_data=f"quota:{code}"))
    done_btn = InlineKeyboardButton("✅ Done", callback_data="quota:done")
    return InlineKeyboardMarkup([buttons[i:i + 1] for i in range(0, len(buttons), 1)] + [[done_btn]])


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
    ctx.user_data["selected_cats"] = {"OPEN"}
    q = ctx.user_data["rank"]
    await u.message.reply_text(
        f"Rank: <b>{q}</b>\n\nPick your <b>categories</b> (tap to toggle, then Done):",
        reply_markup=_category_kb(ctx.user_data["selected_cats"]),
        parse_mode=ParseMode.HTML,
    )
    return CATEGORY


async def toggle_category(u: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = u.callback_query
    await q.answer()
    payload = q.data.split(":", 1)[1]

    if "selected_cats" not in ctx.user_data:
        await q.edit_message_text(
            "Session expired. /start to restart.",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END

    if payload == "done":
        if not ctx.user_data["selected_cats"]:
            await q.answer("Select at least one category", show_alert=True)
            return CATEGORY
        ctx.user_data["selected_quotas"] = {"ai", "os"}
        await q.edit_message_text(
            "Categories: <b>{}</b>\n\nPick your <b>quotas</b> (tap to toggle, then Done):".format(
                ", ".join(sorted(ctx.user_data["selected_cats"]))
            ),
            reply_markup=_quota_kb(ctx.user_data["selected_quotas"]),
            parse_mode=ParseMode.HTML,
        )
        return QUOTA

    selected = ctx.user_data["selected_cats"]
    if payload in selected:
        if payload == "OPEN":
            await q.answer("OPEN is always included", show_alert=False)
        else:
            selected.discard(payload)
    else:
        selected.add(payload)
    await q.edit_message_reply_markup(reply_markup=_category_kb(selected))
    return CATEGORY


async def toggle_quota(u: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = u.callback_query
    logger.info("toggle_quota user=%s data=%s user_data_keys=%s", u.effective_user.id, q.data, list(ctx.user_data.keys()))
    await q.answer()
    payload = q.data.split(":", 1)[1]

    if "selected_quotas" not in ctx.user_data:
        logger.warning("toggle_quota: no selected_quotas for user %s", u.effective_user.id)
        await q.edit_message_text(
            "Session expired. /start to restart.",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END

    if payload == "done":
        logger.info("toggle_quota: done pressed user=%s selected=%s", u.effective_user.id, ctx.user_data["selected_quotas"])
        if not ctx.user_data["selected_quotas"]:
            await q.answer("Select at least one quota", show_alert=True)
            return QUOTA

        try:
            existing = await check_lead_exists(u.effective_user.id)
        except Exception as e:
            logger.error("toggle_quota: check_lead_exists failed for user %s: %s", u.effective_user.id, e)
            await q.edit_message_text("Error checking your profile. /start to restart.", parse_mode=ParseMode.HTML)
            return ConversationHandler.END

        if existing:
            ctx.user_data["phone"] = existing["phone_number"]
            ctx.user_data["full_name"] = existing["full_name"]
            logger.info("toggle_quota: user %s has lead, calling _show_results", u.effective_user.id)
            return await _show_results(u, ctx)

        cat_str = ", ".join(sorted(ctx.user_data["selected_cats"]))
        quota_names = [FULL_QUOTA.get(c, c) for c in ctx.user_data["selected_quotas"]]
        logger.info("toggle_quota: user %s no lead, showing phone prompt", u.effective_user.id)
        await q.edit_message_text(
            f"Rank: <b>{ctx.user_data['rank']}</b>\n"
            f"Categories: <b>{cat_str}</b>\n"
            f"Quotas: <b>{', '.join(quota_names)}</b>\n\n"
            "Please share your <b>phone number</b> to view results.",
            parse_mode=ParseMode.HTML,
        )
        kb = ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Share Contact", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await q.message.reply_text(
            "Tap the button below to share your contact:",
            reply_markup=kb,
        )
        return PHONE

    selected = ctx.user_data["selected_quotas"]
    if payload in selected:
        selected.discard(payload)
    else:
        selected.add(payload)
    logger.info("toggle_quota: user %s toggled %s → %s", u.effective_user.id, payload, selected)
    await q.edit_message_reply_markup(reply_markup=_quota_kb(selected))
    return QUOTA


async def got_phone(u: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    contact = u.message.contact
    if contact:
        phone = contact.phone_number
        full_name = contact.first_name or ""
        if contact.last_name:
            full_name += " " + contact.last_name
    else:
        phone = u.message.text.strip()
        full_name = u.effective_user.full_name or ""

    ctx.user_data["phone"] = phone
    ctx.user_data["full_name"] = full_name
    rank = ctx.user_data["rank"]
    cats = sorted(ctx.user_data["selected_cats"])
    quotas = [FULL_QUOTA.get(c, c) for c in sorted(ctx.user_data["selected_quotas"])]

    logger.info("User %s phone: %s rank: %s cats: %s quotas: %s", u.effective_user.id, phone, rank, cats, quotas)

    try:
        await store_lead(
            telegram_user_id=u.effective_user.id,
            phone=phone,
            full_name=full_name,
            rank=rank,
            categories=cats,
            quotas=quotas,
        )
    except Exception as e:
        logger.error("Failed to store lead: %s", e)

    await u.message.reply_text(
        f"Thanks <b>{full_name}</b>!",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.HTML,
    )

    return await _show_results(u, ctx)


async def _show_results(u: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    rank = ctx.user_data["rank"]
    cats = sorted(ctx.user_data["selected_cats"])
    quotas = [FULL_QUOTA.get(c, c) for c in sorted(ctx.user_data["selected_quotas"])]

    msg = u.message or (u.callback_query.message if u.callback_query else None)
    if not msg:
        logger.error("_show_results: no message available on update")
        return ConversationHandler.END

    await msg.reply_text(
        f"Fetching results for Rank <b>{html.escape(str(rank))}</b>…",
        parse_mode=ParseMode.HTML,
    )

    try:
        rows = await get_neet_options_for_categories(rank, cats, quotas, max_rows=100)
    except Exception as e:
        logger.error("DB error in _show_results: %s", e)
        await msg.reply_text("Could not fetch results. Try again later.")
        return ConversationHandler.END

    if not rows:
        await msg.reply_text(
            f"No colleges found for Rank <b>{html.escape(str(rank))}</b>, Categories <b>{html.escape(', '.join(cats))}</b>.",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END

    ctx.user_data["results"] = rows
    ctx.user_data["results_offset"] = 0
    ctx.user_data["quota_label"] = ", ".join(quotas[:3]) + ("…" if len(quotas) > 3 else "")

    text = _build_results_text(rows, 0, rank, ", ".join(cats), ctx.user_data["quota_label"])
    has_more = len(rows) > 25
    await msg.reply_text(text, reply_markup=_results_kb(has_more), parse_mode=ParseMode.HTML)
    return RESULTS


async def show_more(u: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = u.callback_query
    await q.answer()

    if not ctx.user_data.get("results"):
        await q.edit_message_text(
            "Session expired. /start to restart.",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END

    rows = ctx.user_data.get("results", [])
    offset = ctx.user_data.get("results_offset", 0) + 25
    ctx.user_data["results_offset"] = offset

    rank = ctx.user_data["rank"]
    cat_str = ", ".join(sorted(ctx.user_data["selected_cats"]))
    quota_label = ctx.user_data.get("quota_label", "")

    text = _build_results_text(rows, offset, rank, cat_str, quota_label)
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


def _trunc(text: str, max_len: int = 25) -> str:
    return text[:max_len] if len(text) <= max_len else text[:max_len - 1] + "…"


def _pad(text: str, width: int) -> str:
    # Pad to fixed width for table columns
    t = _trunc(text, width)
    # Use simple left padding with spaces
    return t + " " * (width - len(t))


def _build_results_text(rows: list, offset: int, rank: int, cat: str, quota_label: str) -> str:
    total = len(rows)
    end = min(offset + 25, total)
    header = f"📊 <b>Results for Rank {html.escape(str(rank))} ({html.escape(cat)})</b>\n"
    header += f"<i>Showing {offset + 1}-{end} of {total} colleges</i>\n\n"

    lines = []
    for i, row in enumerate(rows[offset:end], start=offset + 1):
        name = html.escape(_trunc(row.get("institution_name", "?"), 35))
        prog = html.escape(_trunc(row.get("program_code", ""), 12))
        ql = html.escape(_trunc(row.get("quota_label", ""), 15))
        o = str(row.get("opening_rank", "") or "")
        c = str(row.get("closing_rank", "") or "")
        rank_str = f"{o}→{c}" if o and c else "N/A"
        rnd = html.escape(_trunc(str(row.get("round_key", "")), 6))
        lines.append(
            f"<b>{i}.</b> {name}\n"
            f"   <code>{prog}</code> | {ql}\n"
            f"   Rank: <code>{rank_str}</code> | {rnd}\n"
        )

    text = header + "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n… <i>(truncated)</i>"
    return text


def _results_kb(has_more: bool) -> InlineKeyboardMarkup:
    buttons = []
    if has_more:
        buttons.append(InlineKeyboardButton("📋 Show More", callback_data="more"))
    buttons.append(InlineKeyboardButton("🔄 Start Over", callback_data="restart"))
    return InlineKeyboardMarkup([buttons])


async def cancel(u: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    await u.message.reply_text("Cancelled. /start to restart.")
    return ConversationHandler.END


async def help_cmd(u: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await u.message.reply_text(
        "<b>How to use</b>\n"
        "1. /start\n"
        "2. Enter your NEET All India Rank\n"
        "3. Pick categories (tap to toggle, then Done)\n"
        "4. Pick quotas (tap to toggle, then Done)\n"
        "5. Share your phone contact\n"
        "6. See available colleges\n\n"
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
            CATEGORY: [CallbackQueryHandler(toggle_category, pattern=r"^cat:")],
            QUOTA: [CallbackQueryHandler(toggle_quota, pattern=r"^quota:")],
            PHONE: [
                MessageHandler(filters.CONTACT, got_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, got_phone),
            ],
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
