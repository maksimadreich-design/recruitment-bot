import asyncio
import logging
import os
import sys
from aiohttp import web
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

async def start_web_server(port: int):
    """Start async web server for Render health checks."""
    app = web.Application()
    async def health(request):
        return web.Response(text="OK - AI Recruitment Bot is live 24/7 on Render!")

    app.router.add_get("/", health)
    app.router.add_get("/healthz", health)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Health check web server running on 0.0.0.0:%d", port)
    return runner

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

    logger.info("Initializing SQLite database...")
    await db.init_db()

    # Start health check server on port assigned by Render or default 10000
    port = int(os.environ.get("PORT", "10000"))
    web_runner = await start_web_server(port)

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
        await web_runner.cleanup()
        logger.info("Bot session closed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user.")
