"""
bot.py — Telegram bot front-end for the expense tracker.

Plain text messages are parsed (parser.py), stored (db.py), and immediately
re-exported (export.py) so dashboard.html is always up to date.

Commands:
    /start   — welcome + quick instructions
    /help    — usage examples
    /total   — this month's spend vs budget, with a text progress bar
    /undo    — delete the most recently logged entry
    /budget  — show per-category caps

Run with:  python bot.py
Requires:  pip install python-telegram-bot
"""

import json
import logging
import os
import asyncio
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import db
import export
from parser import parse_message

load_dotenv()

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"

CATEGORY_EMOJIS = {
    "rent": "🏠",
    "food": "🍛",
    "groceries": "🛒",
    "travel": "🚇",
    "bills": "💡",
    "emis": "💳",
    "insurance": "🛡️",
    "investments": "📈",
    "emergency": "🚑",
    "clothes": "👕",
    "luxuries": "🎉",
    "health": "💪",
    "education": "📚",
    "other": "📦"
}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def load_config():
    return export.load_config()


def fmt_money(value, currency="₹"):
    """Format a number in Indian digit grouping, e.g. 1234567 -> 12,34,567."""
    value = round(value)
    s = str(abs(int(value)))
    if len(s) <= 3:
        grouped = s
    else:
        last3 = s[-3:]
        rest = s[:-3]
        parts = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        grouped = ",".join(parts) + "," + last3
    sign = "-" if value < 0 else ""
    return f"{sign}{currency}{grouped}"


def progress_bar(spent, budget, width=14):
    if budget <= 0:
        return "[no budget set]"
    pct = spent / budget
    filled = min(width, round(pct * width))
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {pct * 100:.0f}%"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Received /start command from chat_id: %s", update.effective_chat.id)
    await update.message.reply_text(
        "Expense Tracker bot is live.\n\n"
        "Just text me what you spent, in plain English:\n"
        "  • spent 500 on ola\n"
        "  • swiggy 420 dinner\n"
        "  • 1.5k myntra shirt\n"
        "  • got salary 75000\n\n"
        "Commands: /total  /undo  /budget  /help"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Received /help command from chat_id: %s", update.effective_chat.id)
    await update.message.reply_text(
        "How to log spending — just type it naturally:\n\n"
        "  spent 500 on ola          -> travel, ₹500\n"
        "  swiggy 420 dinner         -> food, ₹420\n"
        "  1.5k myntra shirt         -> clothes, ₹1,500\n"
        "  2l invested in mutual fund-> investments, ₹2,00,000\n"
        "  got salary 75000          -> income, ₹75,000\n\n"
        "Amount formats understood: 500, 1,250, 1.5k, 2l, rs 500, ₹500, 500rs\n\n"
        "Commands:\n"
        "  /total   — this month's spend vs budget\n"
        "  /undo    — remove the last entry you logged\n"
        "  /budget  — show your per-category caps\n"
    )


async def total_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = load_config()
    month = date.today().strftime("%Y-%m")
    spent = db.month_total(month)
    budget = cfg.get("monthlyBudget", 0)
    currency = cfg.get("currency", "₹")

    bar = progress_bar(spent, budget)
    remaining = budget - spent
    remaining_text = (
        f"{fmt_money(remaining, currency)} left"
        if remaining >= 0
        else f"{fmt_money(-remaining, currency)} over budget"
    )

    await update.message.reply_text(
        f"This month ({month}):\n"
        f"Spent: {fmt_money(spent, currency)} / {fmt_money(budget, currency)}\n"
        f"{bar}\n"
        f"{remaining_text}"
    )


async def budget_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = load_config()
    currency = cfg.get("currency", "₹")
    budgets = cfg.get("budgets", {})
    month = date.today().strftime("%Y-%m")
    spent_by_cat = db.category_totals(month)

    lines = ["Category budgets this month:"]
    for cat, cap in budgets.items():
        spent = spent_by_cat.get(cat, 0)
        flag = " ⚠️" if spent > cap else ""
        emoji = CATEGORY_EMOJIS.get(cat, "📦")
        lines.append(f"  {emoji} {cat.capitalize()}: {fmt_money(spent, currency)} / {fmt_money(cap, currency)}{flag}")
    await update.message.reply_text("\n".join(lines))


async def undo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    deleted = db.undo_last(chat_id=chat_id)
    export.export()
    if deleted is None:
        await update.message.reply_text("Nothing to undo.")
        return
    cfg = load_config()
    currency = cfg.get("currency", "₹")
    emoji = CATEGORY_EMOJIS.get(deleted['category'], '📦')
    cat_name = f"{emoji} {deleted['category'].capitalize()}"
    await update.message.reply_text(
        f"Removed: {cat_name} {fmt_money(deleted['amount'], currency)} "
        f"({deleted['note']})"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Received message from chat_id: %s - Content: %r", update.effective_chat.id, update.message.text)
    text = update.message.text
    chat_id = update.effective_chat.id

    parsed = parse_message(text)
    if parsed is None:
        await update.message.reply_text(
            "Couldn't find an amount in that message. Try something like "
            "'spent 500 on ola' or '1.5k myntra shirt'."
        )
        return

    db.add(
        amount=parsed["amount"],
        category=parsed["category"],
        note=parsed["note"],
        txn_type=parsed["type"],
        chat_id=chat_id,
    )
    export.export()

    cfg = load_config()
    currency = cfg.get("currency", "₹")

    if parsed["type"] == "income":
        await update.message.reply_text(
            f"✅ Logged income: {fmt_money(parsed['amount'], currency)} ({parsed['note']})"
        )
        return

    month = date.today().strftime("%Y-%m")
    spent = db.month_total(month)
    budget = cfg.get("monthlyBudget", 0)
    bar = progress_bar(spent, budget)

    emoji = CATEGORY_EMOJIS.get(parsed['category'], '📦')
    cat_name = f"{emoji} {parsed['category'].capitalize()}"
    await update.message.reply_text(
        f"✅ {cat_name} · {fmt_money(parsed['amount'], currency)} "
        f"({parsed['note']})\n"
        f"Month total: {fmt_money(spent, currency)} / {fmt_money(budget, currency)}\n"
        f"{bar}"
    )


def start_http_server(app, main_loop, port, webhook_path, blocking=False):
    import http.server
    import threading

    class ExpenseHTTPHandler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            logger.info("HTTP Request: %s - - %s", self.address_string(), format % args)

        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_GET(self):
            if self.path == "/":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                dashboard_path = BASE_DIR / "dashboard.html"
                if dashboard_path.exists():
                    self.wfile.write(dashboard_path.read_bytes())
                else:
                    self.wfile.write(b"dashboard.html not found.")
            elif self.path == "/data.js":
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Type", "application/javascript; charset=utf-8")
                self.end_headers()
                js_data = export.export()
                self.wfile.write(js_data.encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            if webhook_path and self.path == webhook_path:
                try:
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length)
                    data = json.loads(body.decode('utf-8'))
                    
                    update = Update.de_json(data, app.bot)
                    future = asyncio.run_coroutine_threadsafe(app.update_queue.put(update), main_loop)
                    future.result(timeout=5)
                    
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"OK")
                except Exception as e:
                    logger.error("Error processing webhook update: %s", e)
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(str(e).encode('utf-8'))
            elif self.path == "/api/config":
                try:
                    content_length = int(self.headers.get('Content-Length', 0))
                    post_data = self.rfile.read(content_length)
                    data = json.loads(post_data.decode('utf-8'))
                    
                    cfg = export.load_config()
                    cfg["monthlyBudget"] = float(data.get("monthlyBudget", cfg.get("monthlyBudget", 0)))
                    cfg["budgets"] = data.get("budgets", cfg.get("budgets", {}))
                    
                    try:
                        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                            json.dump(cfg, f, indent=2)
                    except OSError:
                        pass  # Ignore if config.json is on a read-only filesystem
                        
                    export.export()
                    
                    self.send_response(200)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    response = {"status": "success", "config": {
                        "monthlyBudget": cfg["monthlyBudget"],
                        "budgets": cfg["budgets"]
                    }}
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                except Exception as e:
                    logger.error("Error updating config via HTTP: %s", e)
                    self.send_response(500)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()

    server = http.server.ThreadingHTTPServer(("0.0.0.0", port), ExpenseHTTPHandler)
    logger.info("HTTP config and web server starting on http://0.0.0.0:%d…", port)
    
    if blocking:
        server.serve_forever()
    else:
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()


def main():
    db.init_db()
    export.export()  # make sure dashboard has data the moment the bot starts

    cfg = load_config()
    token = os.environ.get("TELEGRAM_TOKEN") or cfg.get("telegram_token", "")
    if not token or token.startswith("PUT_YOUR"):
        raise SystemExit(
            "No Telegram token configured. Edit config.json or set the "
            "TELEGRAM_TOKEN environment variable."
        )

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("total", total_cmd))
    app.add_handler(CommandHandler("undo", undo_cmd))
    app.add_handler(CommandHandler("budget", budget_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    webhook_url = os.environ.get("RENDER_EXTERNAL_URL")
    
    if webhook_url:
        # Webhook mode (cloud deployment)
        try:
            main_loop = asyncio.get_running_loop()
        except RuntimeError:
            main_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(main_loop)
        
        main_loop.run_until_complete(app.initialize())
        main_loop.run_until_complete(app.start())
        
        # Setup telegram webhook with token path for security
        webhook_path = f"/webhook/{token.replace(':', '_')}"
        full_webhook_url = f"{webhook_url.rstrip('/')}{webhook_path}"
        logger.info("Setting Telegram Webhook to: %s", full_webhook_url)
        main_loop.run_until_complete(app.bot.set_webhook(url=full_webhook_url))
        
        port = int(os.environ.get("PORT", 8000))
        try:
            start_http_server(app, main_loop, port, webhook_path, blocking=True)
        except KeyboardInterrupt:
            pass
        finally:
            main_loop.run_until_complete(app.stop())
            main_loop.run_until_complete(app.shutdown())
    else:
        # Polling mode (local deployment)
        start_http_server(app, None, 8000, None, blocking=False)
        logger.info("Bot starting — polling for messages…")
        app.run_polling()


if __name__ == "__main__":
    main()
