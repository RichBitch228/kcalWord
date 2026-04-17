import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

from claude_api import parse_food
from storage import (
    add_entry, get_day, get_week, get_month, get_year,
    reset_today, format_entry, format_period_summary, today_key
)

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привіт! Просто напиши що з'їв, наприклад:\n"
        "«200г курки, тарілка рису і яблуко»\n\n"
        "Команди:\n"
        "/today — підсумок за сьогодні\n"
        "/day 16.04 — підсумок за дату\n"
        "/week — останні 7 днів\n"
        "/month — поточний місяць\n"
        "/month 03.2026 — конкретний місяць\n"
        "/year — поточний рік\n"
        "/year 2025 — конкретний рік\n"
        "/reset — скинути сьогоднішній запис"
    )


async def handle_food(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    await update.message.reply_text("⏳ Рахую...")
    try:
        parsed = parse_food(text)
        entry = add_entry(parsed)
        await update.message.reply_text("✅ Додано!\n\n" + format_entry(today_key(), entry))
    except Exception as e:
        logging.error(f"Error processing food: {type(e).__name__}: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Помилка: {type(e).__name__}: {e}")


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = today_key()
    entry = get_day(key)
    if not entry:
        await update.message.reply_text("За сьогодні ще нічого не записано.")
        return
    await update.message.reply_text(format_entry(key, entry))


async def cmd_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Вкажи дату: /day 16.04")
        return
    entry = get_day(args[0])
    if not entry:
        await update.message.reply_text(f"Нема записів за {args[0]}.")
        return
    await update.message.reply_text(format_entry(args[0], entry))


async def cmd_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    week = get_week()
    if not week:
        await update.message.reply_text("За останні 7 днів нема записів.")
        return
    await update.message.reply_text("\n\n".join(format_entry(k, v) for k, v in week))


async def cmd_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    month_str = context.args[0] if context.args else None
    entries = get_month(month_str)
    label = month_str or "цей місяць"
    await update.message.reply_text(format_period_summary(label, entries))


async def cmd_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    year_str = context.args[0] if context.args else None
    entries = get_year(year_str)
    label = year_str or "цей рік"
    await update.message.reply_text(format_period_summary(label, entries))


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_today()
    await update.message.reply_text(f"🗑 Запис за {today_key()} видалено.")


def main():
    token = os.environ["TELEGRAM_TOKEN"]
    request = HTTPXRequest(connect_timeout=30, read_timeout=30)
    app = ApplicationBuilder().token(token).request(request).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("day", cmd_day))
    app.add_handler(CommandHandler("week", cmd_week))
    app.add_handler(CommandHandler("month", cmd_month))
    app.add_handler(CommandHandler("year", cmd_year))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_food))
    logging.info("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
