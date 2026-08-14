"""
aiogram 3.x Bot and Dispatcher setup.
"""
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.utils.logger import logger

# Token verification
if not settings.telegram_bot_token:
    logger.warning("TELEGRAM_BOT_TOKEN is not set in environment or .env file.")

# Initialize aiogram Bot instance
bot = Bot(
    token=settings.telegram_bot_token or "123456789:dummytokenforinitialization",
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# Initialize Dispatcher
dp = Dispatcher(storage=MemoryStorage())
