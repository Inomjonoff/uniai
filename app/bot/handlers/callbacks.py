"""
Inline button callback query handlers.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy import select

from app.db.session import async_session_factory
from app.db.models import Setting, TelegramGroup, Feedback
from app.knowledge.repository import KnowledgeRepository
from app.bot.keyboards.inline import (
    get_settings_keyboard,
    get_group_item_keyboard,
    get_group_settings_keyboard
)
from app.config import settings

callback_router = Router()


@callback_router.callback_query(F.data == "menu:refresh_settings")
async def cb_refresh_settings(callback: CallbackQuery):
    async with async_session_factory() as session:
        repo = KnowledgeRepository(session)
        groups = await repo.get_all_groups()
        total_k = await repo.get_total_knowledge_count()

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

    await callback.message.edit_text(
        text,
        reply_markup=get_settings_keyboard(
            groups_count=len(groups),
            knowledge_count=total_k,
            auto_learning=auto_learn_val,
            screenshot_analysis=vision_val
        )
    )
    await callback.answer("Yangilandi")


@callback_router.callback_query(F.data.startswith("toggle:"))
async def cb_toggle_setting(callback: CallbackQuery):
    key = callback.data.split(":")[1]
    async with async_session_factory() as session:
        stmt = select(Setting).where(Setting.key == key)
        res = await session.execute(stmt)
        setting = res.scalar_one_or_none()
        if setting:
            setting.value_json = not bool(setting.value_json)
            await session.commit()

    await cb_refresh_settings(callback)


@callback_router.callback_query(F.data == "menu:groups")
async def cb_show_groups(callback: CallbackQuery):
    async with async_session_factory() as session:
        repo = KnowledgeRepository(session)
        groups = await repo.get_all_groups()

    if not groups:
        await callback.answer("Hozircha guruhlar mavjud emas.", show_alert=True)
        return

    text = "👥 <b>Kuzatilayotgan guruhlar ro'yxati:</b>\nSozlash uchun guruhni bosing:"
    await callback.message.edit_text(text, reply_markup=get_group_item_keyboard(groups))
    await callback.answer()


@callback_router.callback_query(F.data.startswith("group_cfg:"))
async def cb_group_config(callback: CallbackQuery):
    chat_id = int(callback.data.split(":")[1])
    async with async_session_factory() as session:
        stmt = select(TelegramGroup).where(TelegramGroup.chat_id == chat_id)
        res = await session.execute(stmt)
        group = res.scalar_one_or_none()

    if not group:
        await callback.answer("Guruh topilmadi.", show_alert=True)
        return

    text = (
        f"👥 <b>Guruh:</b> {group.title}\n"
        f"🆔 <code>{group.chat_id}</code>\n\n"
        f"• <b>Learning:</b> {'🟢 ON' if group.learning_enabled else '🔴 OFF'}\n"
        f"• <b>Reply:</b> {'🟢 ON' if group.reply_enabled else '🔴 OFF (Faqat jim kuzatadi)'}\n"
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_group_settings_keyboard(
            chat_id=group.chat_id,
            group_title=group.title,
            learning_on=group.learning_enabled,
            reply_on=group.reply_enabled
        )
    )
    await callback.answer()


@callback_router.callback_query(F.data.startswith("grp_toggle_learn:"))
async def cb_grp_toggle_learn(callback: CallbackQuery):
    chat_id = int(callback.data.split(":")[1])
    async with async_session_factory() as session:
        repo = KnowledgeRepository(session)
        stmt = select(TelegramGroup).where(TelegramGroup.chat_id == chat_id)
        res = await session.execute(stmt)
        group = res.scalar_one_or_none()
        if group:
            await repo.update_group_settings(chat_id=chat_id, learning=not group.learning_enabled)

    # Re-render group config
    await cb_group_config(callback)


@callback_router.callback_query(F.data.startswith("grp_toggle_reply:"))
async def cb_grp_toggle_reply(callback: CallbackQuery):
    chat_id = int(callback.data.split(":")[1])
    async with async_session_factory() as session:
        repo = KnowledgeRepository(session)
        stmt = select(TelegramGroup).where(TelegramGroup.chat_id == chat_id)
        res = await session.execute(stmt)
        group = res.scalar_one_or_none()
        if group:
            await repo.update_group_settings(chat_id=chat_id, reply=not group.reply_enabled)

    # Re-render group config
    await cb_group_config(callback)


@callback_router.callback_query(F.data.startswith("confirm:"))
async def cb_confirm_action(callback: CallbackQuery):
    action = callback.data.split(":")[1]
    if action == "delete_all":
        async with async_session_factory() as session:
            repo = KnowledgeRepository(session)
            deleted_count = await repo.delete_all_knowledge()
        await callback.message.edit_text(f"Barcha bilimlar bazasi tozalandi ({deleted_count:,} ta yozuv o'chirildi).")
        await callback.answer("Baza tozalandi.")
    else:
        await callback.answer("Amal bajarildi.")


@callback_router.callback_query(F.data.startswith("cancel:"))
async def cb_cancel_action(callback: CallbackQuery):
    await callback.message.edit_text("Amal bekor qilindi.")
    await callback.answer("Bekor qilindi.")


@callback_router.callback_query(F.data == "menu:close")
async def cb_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@callback_router.callback_query(F.data.startswith("fb:"))
async def cb_feedback(callback: CallbackQuery):
    parts = callback.data.split(":")
    rating_type = "thumbs_up" if parts[1] == "up" else "thumbs_down"
    kid = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() and int(parts[2]) > 0 else None

    async with async_session_factory() as session:
        fb = Feedback(
            knowledge_id=kid,
            telegram_user_id=callback.from_user.id,
            rating=rating_type
        )
        session.add(fb)
        await session.commit()

    await callback.answer("Fikringiz uchun rahmat! 👍" if rating_type == "thumbs_up" else "Qabul qilindi.")
