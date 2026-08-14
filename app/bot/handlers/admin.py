"""
Admin settings and status handlers.
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ChatType
from sqlalchemy import select

from app.db.session import async_session_factory
from app.db.models import Setting, TelegramGroup
from app.knowledge.repository import KnowledgeRepository
from app.bot.keyboards.inline import get_settings_keyboard, get_group_item_keyboard
from app.config import settings

admin_router = Router()
admin_router.message.filter(F.chat.type == ChatType.PRIVATE)


async def show_settings_menu(message: Message):
    """Renders the main settings dashboard."""
    async with async_session_factory() as session:
        repo = KnowledgeRepository(session)
        groups = await repo.get_all_groups()
        total_k = await repo.get_total_knowledge_count()

        # Query settings
        stmt_learn = select(Setting).where(Setting.key == "auto_learning")
        res_learn = await session.execute(stmt_learn)
        s_learn = res_learn.scalar_one_or_none()
        auto_learn_val = s_learn.value_json if s_learn else True

        stmt_vision = select(Setting).where(Setting.key == "screenshot_analysis")
        res_vision = await session.execute(stmt_vision)
        s_vision = res_vision.scalar_one_or_none()
        vision_val = s_vision.value_json if s_vision else True

    text = (
        "⚙️ <b>Sozlamalar va Tizim Holati</b>\n\n"
        f"• <b>Gemini API:</b> 🟢 Faol ({settings.gemini_model})\n"
        f"• <b>Auto Learning:</b> {'🟢 ON' if auto_learn_val else '🔴 OFF'}\n"
        f"• <b>Screenshot Vision:</b> {'🟢 ON' if vision_val else '🔴 OFF'}\n"
        f"• <b>Ulangan guruhlar:</b> {len(groups)} ta\n"
        f"• <b>Bilimlar bazasi:</b> {total_k:,} ta yozuv\n"
    )

    await message.answer(
        text,
        reply_markup=get_settings_keyboard(
            groups_count=len(groups),
            knowledge_count=total_k,
            auto_learning=auto_learn_val,
            screenshot_analysis=vision_val
        )
    )


@admin_router.message(Command("settings"))
@admin_router.message(Command("sozlamalar"))
async def cmd_settings(message: Message):
    await show_settings_menu(message)


@admin_router.message(Command("groups"))
async def cmd_groups(message: Message):
    """Lists all monitored Telegram groups."""
    async with async_session_factory() as session:
        repo = KnowledgeRepository(session)
        groups = await repo.get_all_groups()

    if not groups:
        await message.answer("Hozircha bot hech qanday guruhga qo'shilmagan.")
        return

    text = "👥 <b>Kuzatilayotgan guruhlar ro'yxati:</b>\nSozlash uchun guruhni tanlang:"
    await message.answer(text, reply_markup=get_group_item_keyboard(groups))
