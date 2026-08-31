import asyncio
import logging
import os
import sys
import aiohttp
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, JSONResponse
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

bot_task = None
keep_alive_task = None
bot_instance: Bot = None
dp_instance: Dispatcher = None

RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://recruitment-bot-5i3h.onrender.com").rstrip("/")
WEBHOOK_URL = f"{RENDER_URL}/webhook"

async def keep_alive_loop():
    """Keeps Render awake 24/7 by pinging itself every 5 minutes."""
    ping_url = f"{RENDER_URL}/healthz"
    await asyncio.sleep(60)
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(ping_url, timeout=10) as resp:
                    logger.info("Keep-alive self ping: status %d", resp.status)
        except Exception as e:
            logger.debug("Keep-alive ping note: %s", e)
        await asyncio.sleep(300) # Every 5 minutes

async def run_bot():
    global bot_instance, dp_instance
    try:
        logger.info("Initializing SQLite database...")
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
            logger.info("Telegram Webhook set successfully to %s", WEBHOOK_URL)
        except Exception as e:
            logger.error("Failed to set webhook: %s", e)

        logger.info("Bot background worker initialized successfully.")
    except Exception as e:
        logger.error("Error in bot background task: %s", e, exc_info=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_task, keep_alive_task
    logger.info("FastAPI Server starting up on Render...")
    bot_task = asyncio.create_task(run_bot())
    keep_alive_task = asyncio.create_task(keep_alive_loop())
    yield
    logger.info("FastAPI Server shutting down...")
    if bot_task:
        bot_task.cancel()
    if keep_alive_task:
        keep_alive_task.cancel()
    if bot_instance:
        await bot_instance.session.close()

app = FastAPI(title="AI Recruitment Bot", lifespan=lifespan)

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Processes incoming Telegram updates via Webhook."""
    try:
        data = await request.json()
        if bot_instance and dp_instance:
            update = Update.model_validate(data, context={"bot": bot_instance})
            await dp_instance.feed_update(bot_instance, update)
        return JSONResponse(content={"ok": True})
    except Exception as e:
        logger.error("Error in webhook update: %s", e, exc_info=True)
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)

@app.get("/", response_class=PlainTextResponse)
async def root():
    return "OK - AI Recruitment Bot is live 24/7 on Render!"

@app.get("/healthz", response_class=PlainTextResponse)
async def healthz():
    return "OK"

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "10000"))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
