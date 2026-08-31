import asyncio
import logging
import os
import sys
import aiohttp
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

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
bot_instance = None
dp_instance = None

async def keep_alive_loop():
    """Keeps Render free service awake 24/7 by pinging itself every 8 minutes."""
    url = os.environ.get("RENDER_EXTERNAL_URL", "https://recruitment-bot-5i3h.onrender.com") + "/healthz"
    await asyncio.sleep(60) # Wait 1 minute after boot
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    logger.info("Keep-alive self ping: status %d", resp.status)
        except Exception as e:
            logger.debug("Keep-alive ping note: %s", e)
        await asyncio.sleep(480) # 8 minutes

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
            await bot_instance.delete_webhook(drop_pending_updates=True)
        except Exception as e:
            logger.warning("Webhook drop: %s", e)

        logger.info("Telegram Bot Polling started successfully on Render!")
        await dp_instance.start_polling(bot_instance, allowed_updates=dp_instance.resolve_used_update_types())
    except asyncio.CancelledError:
        logger.info("Bot background task cancelled.")
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

@app.get("/", response_class=PlainTextResponse)
async def root():
    return "OK - AI Recruitment Bot is live and running 24/7 on Render!"

@app.get("/healthz", response_class=PlainTextResponse)
async def healthz():
    return "OK"

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "10000"))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
