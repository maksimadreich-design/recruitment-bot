import asyncio
import logging
import os
import sys
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update

from config import config
from database.db import db
from bot.handlers import bot_router
from admin.handlers import admin_router
from main import setup_bot_commands

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("server")

bot_instance: Bot = None
dp_instance: Dispatcher = None
keep_alive_task = None

RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://recruitment-bot-5i3h.onrender.com").rstrip("/")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{RENDER_URL}{WEBHOOK_PATH}"

async def keep_alive_loop():
    """Keeps Render awake by pinging itself periodically."""
    ping_url = f"{RENDER_URL}/healthz"
    await asyncio.sleep(30)
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(ping_url, timeout=10) as resp:
                    logger.info("Keep-alive ping to %s: %d", ping_url, resp.status)
        except Exception as e:
            logger.debug("Keep-alive ping note: %s", e)
        await asyncio.sleep(300) # Every 5 minutes

async def telegram_webhook_handler(request: web.Request) -> web.Response:
    """Processes incoming Telegram updates via Webhook."""
    try:
        data = await request.json()
        update = Update.model_validate(data, context={"bot": bot_instance})
        await dp_instance.feed_update(bot_instance, update)
        return web.json_response({"ok": True})
    except Exception as e:
        logger.error("Error processing update: %s", e, exc_info=True)
        return web.json_response({"ok": False, "error": str(e)}, status=500)

async def healthz_handler(request: web.Request) -> web.Response:
    return web.Response(text="OK", content_type="text/plain")

async def root_handler(request: web.Request) -> web.Response:
    return web.Response(text="OK - AI Recruitment Bot is live 24/7 on Render (Webhook Mode)!", content_type="text/plain")

async def on_startup(app: web.Application):
    global bot_instance, dp_instance, keep_alive_task
    logger.info("Starting AI Recruitment Bot on Render...")
    await db.init_db()

    bot_instance = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp_instance = Dispatcher(storage=MemoryStorage())
    dp_instance.include_router(admin_router)
    dp_instance.include_router(bot_router)

    await setup_bot_commands(bot_instance)

    try:
        await bot_instance.set_webhook(
            url=WEBHOOK_URL,
            drop_pending_updates=True,
            allowed_updates=dp_instance.resolve_used_update_types()
        )
        logger.info("Telegram Webhook set successfully to: %s", WEBHOOK_URL)
    except Exception as e:
        logger.error("Failed to set webhook: %s", e)

    keep_alive_task = asyncio.create_task(keep_alive_loop())

async def on_shutdown(app: web.Application):
    global keep_alive_task, bot_instance
    logger.info("Shutting down bot server...")
    if keep_alive_task:
        keep_alive_task.cancel()
    if bot_instance:
        try:
            await bot_instance.delete_webhook()
        except Exception:
            pass
        await bot_instance.session.close()

async def create_app() -> web.Application:
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, telegram_webhook_handler)
    app.router.add_get("/healthz", healthz_handler)
    app.router.add_get("/", root_handler)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app = loop.run_until_complete(create_app())
    web.run_app(app, host="0.0.0.0", port=port)
