"""
Group and Supergroup message handlers for UNICON-SOFT AI Assistant.
Functions as a silent observer by default (Learning = ON, Reply = OFF),
with support for mentions, reply mode toggle (/reply_on, /reply_off), and intelligent Q&A.
"""
import re
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ChatType
from sqlalchemy import select

from app.db.session import async_session_factory
from app.db.models import TelegramGroup
from app.knowledge.repository import KnowledgeRepository
from app.ai.agent import AssistantAgent
from app.config import settings
from app.utils.telegram_helpers import split_message_text
from app.utils.logger import logger

group_router = Router()
# Filter for groups and supergroups
group_router.message.filter(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))


@group_router.message(Command("reply_on"))
async def cmd_reply_on(message: Message):
    """Enables active AI replies in this group."""
    async with async_session_factory() as session:
        repo = KnowledgeRepository(session)
        group = await repo.get_or_create_group(
            chat_id=message.chat.id,
            title=message.chat.title or "Group",
            username=message.chat.username
        )
        group.reply_enabled = True
        await session.commit()
    
    await message.reply("✅ Ushbu guruhda botning faol javob berish rejimi yoqildi. Endi bot savollarga to'g'ridan-to'g'ri javob beradi.")


@group_router.message(Command("reply_off"))
async def cmd_reply_off(message: Message):
    """Disables active AI replies (switches to silent learner mode)."""
    async with async_session_factory() as session:
        repo = KnowledgeRepository(session)
        group = await repo.get_or_create_group(
            chat_id=message.chat.id,
            title=message.chat.title or "Group",
            username=message.chat.username
        )
        group.reply_enabled = False
        await session.commit()
    
    await message.reply("🔇 Guruhda bot jim rejimga (faqat o'rganish) o'tkazildi. Savol berish uchun botni @positronaibot deb tag qiling.")


@group_router.message()
async def handle_group_message(message: Message, bot: Bot):
    """
    Listens to messages in technical groups.
    Stores raw messages and silently triggers background learning without spamming.
    Replies when mentioned or when reply_enabled is True.
    """
    chat_id = message.chat.id
    group_title = message.chat.title or f"Group {chat_id}"
    sender_name = message.from_user.full_name if message.from_user else "Member"
    username = message.from_user.username if message.from_user else None
    text = message.text or message.caption or ""

    media_type = "text"
    file_id = None
    if message.photo:
        media_type = "photo"
        file_id = message.photo[-1].file_id
    elif message.document:
        media_type = "document"
        file_id = message.document.file_id

    # 1. Store message in database
    async with async_session_factory() as session:
        repo = KnowledgeRepository(session)
        # Ensure group is registered
        group = await repo.get_or_create_group(
            chat_id=chat_id,
            title=group_title,
            username=message.chat.username
        )

        # Store raw message
        await repo.save_raw_telegram_message(
            message_id=message.message_id,
            chat_id=chat_id,
            user_id=message.from_user.id if message.from_user else None,
            sender_name=sender_name,
            username=username,
            text=text,
            media_type=media_type,
            file_id=file_id,
            reply_to_message_id=message.reply_to_message.message_id if message.reply_to_message else None
        )

    # 2. Check if bot was explicitly mentioned or replied to
    bot_info = await bot.get_me()
    is_mentioned = False
    clean_text = text

    if bot_info.username:
        pattern = re.compile(rf"@{re.escape(bot_info.username)}", re.IGNORECASE)
        if pattern.search(text):
            is_mentioned = True
            clean_text = pattern.sub("", text).strip()

    if message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.id == bot_info.id:
        is_mentioned = True

    # Check if admin is calling the bot directly with "bot ..." or "ai ..."
    if message.from_user and message.from_user.id in settings.admin_ids_set:
        if text.lower().startswith(("bot,", "bot ", "ai,", "ai ")):
            is_mentioned = True
            clean_text = re.sub(r"^(bot|ai)[,\s]+", "", text, flags=re.IGNORECASE).strip()

    # 3. Reply if Reply mode is ON for this group OR explicitly mentioned
    if (group.reply_enabled or is_mentioned) and clean_text.strip():
        async with async_session_factory() as session:
            agent = AssistantAgent(session=session)
            result = await agent.process_user_message(
                telegram_user_id=message.from_user.id if message.from_user else 0,
                user_text=clean_text,
                sender_name=sender_name
            )
            reply = result.get("reply_text")
            if reply:
                chunks = split_message_text(reply)
                for chunk in chunks:
                    await message.reply(chunk)
