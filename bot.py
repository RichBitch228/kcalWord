import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, MenuButtonCommands, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from telegram.request import HTTPXRequest

from claude_api import parse_food
from export import generate_word
from storage import (
    add_entry, get_day, get_week, get_month, get_year,
    reset_today, format_entry, format_period_summary, today_key
)

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

HARDCODED_REPLY = "Я розумію лише їжу 🍽 Напиши що з'їв, наприклад: «200г курки, тарілка рису і яблуко»"

HEART_USER_ID = 1175466521
HEART_STICKER = "CAACAgIAAxkBAAIBY2CCjN6QlSBoP0YAAbXGi9vvIlPeAAIcAQACVp29Cne9HQJKG7AoHgQ"

FOOD_KEYWORDS = {
    "г", "гр", "мл", "л", "кг", "шт", "ккал", "калор",
    "їв", "їла", "з'їв", "з'їла", "випив", "випила", "снідав", "обідав", "вечеряв",
    "сніданок", "обід", "вечеря", "перекус",
    "курка", "м'ясо", "риба", "яйце", "хліб", "каша", "суп", "салат",
    "молоко", "кефір", "йогурт", "сир", "масло", "олія",
    "рис", "гречка", "макарон", "картопл", "овоч", "фрукт", "яблук",
    "банан", "апельсин", "шоколад", "цукор", "кава", "чай",
}


def _looks_like_food(text: str) -> bool:
    lower = text.lower()
    if any(char.isdigit() for char in text):
        return True
    return any(kw in lower for kw in FOOD_KEYWORDS)


def uid(update: Update) -> int:
    return update.effective_user.id


# ── keyboards ──────────────────────────────────────────────

def persistent_kb():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📋 Меню")]],
        resize_keyboard=True,
        input_field_placeholder="Напиши що з'їв..."
    )


def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Статистика", callback_data="menu_stats")],
        [InlineKeyboardButton("📤 Експорт Word", callback_data="menu_export")],
        [InlineKeyboardButton("⚙️ Інше", callback_data="menu_other")],
    ])


def stats_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Сьогодні", callback_data="stats_today"),
         InlineKeyboardButton("📆 Тиждень", callback_data="stats_week")],
        [InlineKeyboardButton("🗓 Місяць", callback_data="stats_month"),
         InlineKeyboardButton("📈 Рік", callback_data="stats_year")],
        [InlineKeyboardButton("◀️ Назад", callback_data="menu_main")],
    ])


def export_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("7 днів", callback_data="export_week"),
         InlineKeyboardButton("Місяць", callback_data="export_month"),
         InlineKeyboardButton("Рік", callback_data="export_year")],
        [InlineKeyboardButton("◀️ Назад", callback_data="menu_main")],
    ])


def other_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑 Скинути сьогодні", callback_data="other_reset")],
        [InlineKeyboardButton("◀️ Назад", callback_data="menu_main")],
    ])


# ── handlers ───────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привіт! Просто напиши що з'їв, наприклад:\n«200г курки, тарілка рису і яблуко»",
        reply_markup=persistent_kb()
    )


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Обери дію:", reply_markup=main_menu_kb())


async def handle_food(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if uid(update) == HEART_USER_ID:
        try:
            await update.message.reply_sticker(HEART_STICKER)
        except Exception:
            await update.message.reply_text("❤️")
        return
    if text == "📋 Меню":
        await update.message.reply_text("Обери дію:", reply_markup=main_menu_kb())
        return
    if not _looks_like_food(text):
        await update.message.reply_text(HARDCODED_REPLY)
        return
    await update.message.reply_text("⏳ Рахую...")
    try:
        parsed = parse_food(text)
        entry = add_entry(uid(update), parsed)
        await update.message.reply_text("✅ Додано!\n\n" + format_entry(today_key(), entry))
    except Exception as e:
        logging.error(f"Error: {type(e).__name__}: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Помилка: {type(e).__name__}: {e}")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user.id

    # navigation
    if data == "menu_main":
        await query.edit_message_text("Обери дію:", reply_markup=main_menu_kb())
        return
    if data == "menu_stats":
        await query.edit_message_text("📊 Статистика:", reply_markup=stats_menu_kb())
        return
    if data == "menu_export":
        await query.edit_message_text("📤 Експорт Word:", reply_markup=export_menu_kb())
        return
    if data == "menu_other":
        await query.edit_message_text("⚙️ Інше:", reply_markup=other_menu_kb())
        return

    # stats
    if data == "stats_today":
        key = today_key()
        entry = get_day(user, key)
        text = format_entry(key, entry) if entry else "За сьогодні ще нічого не записано."
        await query.edit_message_text(text, reply_markup=stats_menu_kb())
    elif data == "stats_week":
        week = get_week(user)
        text = "\n\n".join(format_entry(k, v) for k, v in week) if week else "За останні 7 днів нема записів."
        await query.edit_message_text(text, reply_markup=stats_menu_kb())
    elif data == "stats_month":
        entries = get_month(user)
        await query.edit_message_text(format_period_summary("цей місяць", entries), reply_markup=stats_menu_kb())
    elif data == "stats_year":
        entries = get_year(user)
        await query.edit_message_text(format_period_summary("цей рік", entries), reply_markup=stats_menu_kb())

    # export
    elif data in ("export_week", "export_month", "export_year"):
        period = data.split("_")[1]
        if period == "week":
            entries, label = get_week(user), "тиждень"
        elif period == "month":
            entries, label = get_month(user), "місяць"
        else:
            entries, label = get_year(user), "рік"
        if not entries:
            await query.edit_message_text(f"Нема даних для експорту.", reply_markup=export_menu_kb())
            return
        buf = generate_word(entries)
        await query.message.reply_document(
            document=buf,
            filename=f"kcal_{label}.docx",
            caption=f"📄 Лог за {label} — {len(entries)} дн."
        )

    # other
    elif data == "other_reset":
        reset_today(user)
        await query.edit_message_text(f"🗑 Запис за {today_key()} видалено.", reply_markup=other_menu_kb())


async def post_init(app):
    commands = [
        BotCommand("start", "Головне меню"),
        BotCommand("menu", "Відкрити меню"),
        BotCommand("today", "Підсумок за сьогодні"),
        BotCommand("week", "Останні 7 днів"),
        BotCommand("month", "Поточний місяць"),
        BotCommand("year", "Поточний рік"),
        BotCommand("export", "Експорт в Word"),
        BotCommand("reset", "Скинути сьогоднішній запис"),
    ]
    await app.bot.set_my_commands(commands)
    await app.bot.set_chat_menu_button(menu_button=MenuButtonCommands())


def main():
    token = os.environ["TELEGRAM_TOKEN"]
    request = HTTPXRequest(connect_timeout=30, read_timeout=30)
    app = ApplicationBuilder().token(token).request(request).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_food))
    logging.info("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
