
import os

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from database import get_or_create_visitor_id, get_reports

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")


def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Create Link", callback_data="create_link")],
        [InlineKeyboardButton("📊 Reports", callback_data="reports")],
        [InlineKeyboardButton("ℹ️ About", callback_data="about")],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "📱 Device Information Lab\n\n"
        "Generate a test link for a device you own or have permission "
        "to test. The page explains what information is submitted and "
        "requires consent before sending a report.",
        reply_markup=main_keyboard()
    )


async def button_click(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    telegram_user_id = query.from_user.id

    if query.data == "create_link":
        if not PUBLIC_BASE_URL.startswith("https://"):
            await query.message.reply_text(
                "Configure PUBLIC_BASE_URL in .env using your current "
                "HTTPS Cloudflare URL, then restart the bot."
            )
            return

        visitor_id = get_or_create_visitor_id(telegram_user_id)
        link = f"{PUBLIC_BASE_URL}/t/{visitor_id}"

        await query.message.reply_text(
            f"🔗 Your Device Information Lab link:\n\n{link}\n\n"
            "This link is assigned to your Telegram account. "
            "The tester must review the page and consent before "
            "submitting the browser report."
        )

    elif query.data == "reports":
        reports = get_reports(telegram_user_id, limit=5)

        if not reports:
            await query.message.reply_text(
                "No reports saved yet. Reports will appear here "
                "after a tester gives consent and submits the form."
            )
            return

        lines = ["📊 YOUR LATEST REPORTS\n"]

        for item in reports:
            report = item["report"]
            lines.append(
                f"Report #{item['id']}\n"
                f"Visitor ID: {item['visitor_id']}\n"
                f"Time: {item['created_at']}\n"
                f"Browser: {report.get('browser', 'Unknown')}\n"
                f"Platform: {report.get('platform', 'Unknown')}\n"
            )

        text = "\n".join(lines)

        # Keep messages within Telegram's message-length limit.
        await query.message.reply_text(text[:4000])

    elif query.data == "about":
        await query.message.reply_text(
            "ℹ️ Device Information Lab\n\n"
            "This is an educational browser-information demo. "
            "It reads limited browser-exposed details only after "
            "the tester explicitly agrees and submits the report. "
            "It does not access call history, SMS, contacts, "
            "gallery files, camera, or microphone."
        )


def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is missing from .env")

    if not PUBLIC_BASE_URL:
        print("Warning: PUBLIC_BASE_URL is missing from .env")

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_click))

    print("Device Information Lab bot is running...")
    application.run_polling()


if __name__ == "__main__":
    main()
