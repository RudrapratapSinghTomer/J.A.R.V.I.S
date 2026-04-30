#!/usr/bin/env python3
"""
J.A.R.V.I.S Telegram Bot
==========================
Lightweight Telegram gateway — talk to JARVIS from your phone.
Uses python-telegram-bot (free, no billing).

Runs as a separate process alongside main.py:
    python -m tools.telegram_bot

Security:
- Only responds to whitelisted user IDs (from .env)
- Logs all messages
- Rejects unauthorized users with no response
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger("jarvis.telegram")
logs_dir = Path(__file__).parent.parent / "logs"
logs_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            logs_dir / "telegram.log",
            mode="a",
        ),
    ],
)

# Load env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USERS = os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",")
ALLOWED_USERS = [u.strip() for u in ALLOWED_USERS if u.strip()]


def check_config():
    """Validate Telegram config before starting."""
    issues = []
    if not BOT_TOKEN or BOT_TOKEN == "your_token_here":
        issues.append(
            "TELEGRAM_BOT_TOKEN not set in .env\n"
            "  → Get one free from @BotFather on Telegram:\n"
            "    1. Open Telegram, search @BotFather\n"
            "    2. Send /newbot\n"
            "    3. Follow prompts, copy the token\n"
            "    4. Paste into .env as TELEGRAM_BOT_TOKEN=xxx"
        )
    if not ALLOWED_USERS:
        issues.append(
            "TELEGRAM_ALLOWED_USERS not set in .env\n"
            "  → Get your user ID:\n"
            "    1. Open Telegram, search @userinfobot\n"
            "    2. Send /start — it will show your ID\n"
            "    3. Paste into .env as TELEGRAM_ALLOWED_USERS=123456789"
        )
    return issues


def is_authorized(user_id: int) -> bool:
    """Check if user is in the whitelist."""
    return str(user_id) in ALLOWED_USERS


async def run_bot():
    """Start the Telegram bot."""
    try:
        from telegram import Update
        from telegram.ext import (
            ApplicationBuilder,
            CommandHandler,
            MessageHandler,
            ContextTypes,
            filters,
        )
    except ImportError:
        print(
            "❌ python-telegram-bot not installed.\n"
            "   Run: pip install python-telegram-bot\n"
            "   (Already in requirements.txt — just pip install -r requirements.txt)"
        )
        return

    from core.llm_client import brain
    from memory.cognee_bridge import memory as jarvis_memory

    llm = brain
    memory = jarvis_memory
    await memory.initialize()

    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        if update.effective_user is None or update.message is None:
            return
        user_id = update.effective_user.id
        if not is_authorized(user_id):
            logger.warning(f"🔴 Unauthorized /start from user {user_id}")
            return  # Silent reject — don't reveal bot exists to strangers

        await update.message.reply_text(
            "🤖 *J.A.R.V.I.S Online*\n\n"
            "I'm your local AI assistant. Everything runs on your machine.\n"
            "Zero cloud. Zero billing.\n\n"
            "*Commands:*\n"
            "/status — System status\n"
            "/security — Latest security scan\n"
            "/memory <query> — Search my memory\n"
            "/remember <text> — Save to memory\n"
            "/clear — Clear conversation history\n\n"
            "Or just type anything to chat.",
            parse_mode="Markdown",
        )
        logger.info(f"Authorized user {user_id} started session")

    async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status — system health."""
        if update.effective_user is None or update.message is None:
            return
        if not is_authorized(update.effective_user.id):
            return

        health = await llm.health_check()
        now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
        status_lines = [
            "J.A.R.V.I.S Status",
            f"🤖 Ollama: {'✅ Online' if health['ok'] else '❌ Offline'}",
            f"🧠 Model: {llm.model} {'✅' if health.get('model_available') else '⚠️ Not found'}",
            f"📋 Available models: {', '.join(health.get('models', [])) or 'none'}",
            f"⏰ Time: {now_ist.strftime('%H:%M IST')}",
        ]

        if not health["ok"]:
            status_lines.append(f"\n❌ Error: {health.get('error', 'Unknown')}")

        await update.message.reply_text("\n".join(status_lines))

    async def security_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /security — latest scan report."""
        if update.effective_user is None or update.message is None:
            return
        if not is_authorized(update.effective_user.id):
            return

        try:
            from scripts.security_monitor import get_latest_report
            report = get_latest_report()

            if report["ok"]:
                await update.message.reply_text("✅ Security: All clear. No issues found.")
            else:
                warnings = "\n".join(f"  • {w}" for w in report["warnings"])
                await update.message.reply_text(
                    f"SECURITY ALERT\nScan: {report['date']}\n\n{warnings}"
                )
        except Exception as e:
            await update.message.reply_text(f"Security check error: {e}")

    async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /memory <query> — search memory."""
        if update.effective_user is None or update.message is None:
            return
        if not is_authorized(update.effective_user.id):
            return

        query = " ".join(context.args) if context.args else ""
        if not query:
            await update.message.reply_text("Usage: /memory <search query>")
            return

        results = await memory.recall(query, top_k=3)
        if results:
            response = "Memory Search Results:\n\n"
            for i, r in enumerate(results, 1):
                text = r["text"][:300]
                response += f"{i}. {text}\n\n"
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("No memories found for that query.")

    async def remember_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /remember <text> — save to memory."""
        if update.effective_user is None or update.message is None:
            return
        if not is_authorized(update.effective_user.id):
            return

        text = " ".join(context.args) if context.args else ""
        if not text:
            await update.message.reply_text("Usage: /remember <something to save>")
            return

        await memory.remember(
            text,
            metadata={
                "type": "telegram_note",
                "source": "telegram",
                "user_id": str(update.effective_user.id),
                "date": datetime.now().isoformat(),
            },
        )
        await update.message.reply_text(f"Saved to memory: {text[:100]}")

    async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /clear — reset conversation."""
        if update.effective_user is None or update.message is None:
            return
        if not is_authorized(update.effective_user.id):
            return
        llm.clear_history()
        await update.message.reply_text("🗑️ Conversation history cleared.")

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle free-text messages — send to LLM."""
        if update.effective_user is None or update.message is None:
            return
        user_id = update.effective_user.id
        if not is_authorized(user_id):
            logger.warning(f"🔴 Unauthorized message from {user_id}")
            return

        user_text = update.message.text or ""
        if not user_text.strip():
            return
        logger.info(f"[{user_id}] → {user_text[:80]}")

        # Show typing indicator
        await update.message.chat.send_action("typing")

        # Get LLM response
        response = await llm.chat(user_text)
        logger.info(f"[{user_id}] ← {response[:80]}")

        # Telegram has a 4096 char limit per message
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                await update.message.reply_text(response[i:i+4000])
        else:
            await update.message.reply_text(response)

    # Build and start bot
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("security", security_command))
    app.add_handler(CommandHandler("memory", memory_command))
    app.add_handler(CommandHandler("remember", remember_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info(f"Telegram bot starting. Allowed users: {ALLOWED_USERS}")
    print("🤖 J.A.R.V.I.S Telegram Bot running. Press Ctrl+C to stop.")
    
    await app.initialize()
    await app.start()
    if app.updater is None:
        raise RuntimeError("Telegram updater is unavailable; polling cannot start.")
    await app.updater.start_polling(drop_pending_updates=True)
    
    # Keep running until interrupted
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        if app.updater is not None:
            await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    config_issues = check_config()
    if config_issues:
        print("⚠️  Configuration needed before starting:\n")
        for issue in config_issues:
            print(f"  {issue}\n")
        sys.exit(1)

    asyncio.run(run_bot())
