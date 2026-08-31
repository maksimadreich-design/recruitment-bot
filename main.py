import asyncio
import http.server
import logging
import os
import sys
import threading
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault

from config import config
from database.db import db
from bot.handlers import bot_router
from admin.handlers import admin_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class HealthCheckHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"OK - AI Recruitment Bot is live 24/7 on Render!")

    def log_message(self, format, *args):
        # Silence default server access logs to keep log clean
        pass

def run_health_server_in_background(port: int):
    """Run standard Python HTTP server in daemon thread to satisfy Render health check."""
    try:
        server = http.server.ThreadingHTTPServer(("0.0.0.0", port), HealthCheckHandler)
        logger.info("Health check server bound successfully to port %d", port)
        server.serve_forever()
    except Exception as e:
        logger.error("Failed to bind health check server on port %d: %s", port, e)

async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Почати відбір / Головне меню"),
        BotCommand(command="stats", description="[Admin] Статистика AI та рішення власника"),
        BotCommand(command="candidates", description="[Admin] Всі кандидати"),
        BotCommand(command="pending", description="[Admin] Очікують рішення власника"),
        BotCommand(command="top", description="[Admin] Топ-10 за Sales Potential"),
        BotCommand(command="compare", description="[Admin] Порівняти 2 кандидатів (/compare 1 2)"),
        BotCommand(command="strong", description="[Admin] AI: STRONG"),
        BotCommand(command="potential", description="[Admin] AI: POTENTIAL"),
        BotCommand(command="weak", description="[Admin] AI: WEAK"),
        BotCommand(command="rejected", description="[Admin] AI: REJECT_RECOMMENDED"),
        BotCommand(command="interview", description="[Admin] Власник: INTERVIEW"),
        BotCommand(command="test", description="[Admin] Власник: TEST"),
        BotCommand(command="owner_rejected", description="[Admin] Власник: REJECTED"),
        BotCommand(command="reserve", description="[Admin] Власник: RESERVE"),
        BotCommand(command="hired", description="[Admin] Власник: HIRED"),
    ]
    try:
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    except Exception as e:
        logger.warning("Could not set bot commands: %s", e)

async def main():
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN is missing in environment/.env! Please set it before running.")
        sys.exit(1)

    # Start background health server for Render / Cloud
    port_env = os.environ.get("PORT")
    if port_env and port_env.isdigit():
        port = int(port_env)
        t = threading.Thread(target=run_health_server_in_background, args=(port,), daemon=True)
        t.start()

    logger.info("Initializing SQLite database...")
    await db.init_db()

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Register routers (admin router first to handle admin commands and callbacks)
    dp.include_router(admin_router)
    dp.include_router(bot_router)

    await setup_bot_commands(bot)

    # Drop pending updates on startup to avoid processing old requests
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        logger.warning("Webhook drop warning: %s", e)

    logger.info("AI Recruitment Bot successfully started!")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("Bot session closed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user.")
