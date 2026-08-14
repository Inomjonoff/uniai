"""
Inline button callback query handlers.
Handles Group Management, Recent Requests, and Unresolved Knowledge Learning Queue.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from app.db.session import async_session_factory
from app.db.models import Setting, TelegramGroup, Feedback, UnresolvedQuery, TelegramMessage
from app.knowledge.repository import KnowledgeRepository
from app.bot.keyboards.inline import (
    get_settings_keyboard,
    get_group_item_keyboard,
    get_group_settings_keyboard,
    get_unresolved_list_keyboard,
    get_unresolved_detail_keyboard,
    get_recent_messages_keyboard
)
from app.config import settings


class TeachKnowledgeState(StatesGroup):
    waiting_for_solution = State()


callback_router = Router()


@callback_router.callback_query(F.data == "menu:refresh_settings")
async def cb_refresh_settings(callback: CallbackQuery):
    async with async_session_factory() as session:
        repo = KnowledgeRepository(session)
        groups = await repo.get_all_groups()
        total_k = await repo.get_total_knowledge_count()
        pending_items = await repo.get_pending_unresolved_queries(limit=50)

        stmt_learn = select(Setting).where(Setting.key == "auto_learning")
        res_learn = await session.execute(stmt_learn)
        s_learn = res_learn.scalar_one_or_none()
        auto_learn_val = s_learn.value_json if s_learn else True

        stmt_vision = select(Setting).where(Setting.key == "screenshot_analysis")
        res_vision = await session.execute(stmt_vision)
        s_vision = res_vision.scalar_one_or_none()
        vision_val = s_vision.value_json if s_vision else True

    text = (
        "⚙️ <b>UNICON-SOFT AI Boshqaruv Paneli</b>\n\n"
        f"• <b>Gemini AI:</b> 🟢 Faol ({settings.gemini_model})\n"
        f"• <b>Auto Learning:</b> {'🟢 ON' if auto_learn_val else '🔴 OFF'}\n"
        f"• <b>Screenshot Vision:</b> {'🟢 ON' if vision_val else '🔴 OFF'}\n"
        f"• <b>Ulangan guruhlar:</b> {len(groups)} ta\n"
        f"• <b>Bilimlar bazasi:</b> {total_k:,} ta yozuv\n"
        f"• <b>O'rganish kutilayotganlar:</b> {len(pending_items)} ta savol/muammo\n"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_settings_keyboard(
            groups_count=len(groups),
            knowledge_count=total_k,
            pending_learn_count=len(pending_items),
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


# ==========================================================
# GURUHLARNI BOSHQARISH (GROUP MANAGEMENT)
# ==========================================================
@callback_router.callback_query(F.data == "menu:groups")
async def cb_show_groups(callback: CallbackQuery):
    async with async_session_factory() as session:
        repo = KnowledgeRepository(session)
        groups = await repo.get_all_groups()

    if not groups:
        await callback.answer("Hozircha ulangan guruhlar mavjud emas.", show_alert=True)
        return

    text = "👥 <b>Kuzatilayotgan guruhlar ro'yxati:</b>\nSozlash yoki javob berish rejimini o'zgartirish uchun guruhni tanlang:"
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
        f"🆔 ID: <code>{group.chat_id}</code>\n\n"
        f"• <b>O'rganish (Learning):</b> {'🟢 Faol' if group.learning_enabled else '🔴 O\'chirilgan'}\n"
        f"• <b>Javob berish (Reply):</b> {'🟢 Faol (Har bir savolga javob beradi)' if group.reply_enabled else '🔴 O\'chirilgan (Jim kuzatadi)'}\n"
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

    await cb_group_config(callback)


# ==========================================================
# O'RGANISH KUTILAYOTGANLAR (UNRESOLVED KNOWLEDGE QUEUE)
# ==========================================================
@callback_router.callback_query(F.data == "menu:unresolved_queue")
async def cb_unresolved_queue(callback: CallbackQuery):
    async with async_session_factory() as session:
        repo = KnowledgeRepository(session)
        items = await repo.get_pending_unresolved_queries(limit=20)

    if not items:
        text = "🎓 <b>O'rganish navbati bo'sh!</b>\n\nBot AI barcha so'ralgan texnik savollarga yechimga ega."
    else:
        text = f"🎓 <b>O'rganilishi kerak bo'lgan noma'lum mavzular ({len(items)} ta):</b>\nHar bir savolga bitta-bitta yechim o'rgatishingiz mumkin:"

    await callback.message.edit_text(text, reply_markup=get_unresolved_list_keyboard(items))
    await callback.answer()


@callback_router.callback_query(F.data.startswith("unresolved_view:"))
async def cb_unresolved_view(callback: CallbackQuery):
    query_id = int(callback.data.split(":")[1])
    async with async_session_factory() as session:
        repo = KnowledgeRepository(session)
        item = await repo.get_unresolved_query_by_id(query_id)

    if not item:
        await callback.answer("Savol topilmadi yoki allaqachon o'rganilgan.", show_alert=True)
        await cb_unresolved_queue(callback)
        return

    text = (
        f"❓ <b>Noma'lum Savol / Muammo:</b>\n"
        f"<i>“{item.query_text}”</i>\n\n"
        f"👤 <b>Yuborgan:</b> {item.sender_name or 'Noma\'lum'}\n"
        f"📅 <b>Sana:</b> {item.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"Ushbu savolga yechim kiritish uchun pastdagi <b>“✍️ Yechim kiritish”</b> tugmasini bosing:"
    )
    await callback.message.edit_text(text, reply_markup=get_unresolved_detail_keyboard(query_id))
    await callback.answer()


@callback_router.callback_query(F.data.startswith("unresolved_teach:"))
async def cb_unresolved_teach(callback: CallbackQuery, state: FSMContext):
    query_id = int(callback.data.split(":")[1])
    async with async_session_factory() as session:
        repo = KnowledgeRepository(session)
        item = await repo.get_unresolved_query_by_id(query_id)

    if not item:
        await callback.answer("Savol topilmadi.", show_alert=True)
        return

    await state.set_state(TeachKnowledgeState.waiting_for_solution)
    await state.update_data(query_id=query_id, query_text=item.query_text)

    prompt_text = (
        f"✍️ <b>Muammo:</b> <i>“{item.query_text}”</i>\n\n"
        f"Ushbu muammo bo'yicha to'g'ri yechim yoki qoidani quyida yozib yuboring:\n"
        f"(Masalan: <i>Ijro.gov.uzda 502 chiqsa API servisi qayta ishga tushiriladi</i>)"
    )
    await callback.message.answer(prompt_text)
    await callback.answer("Yechimni yozing...")


@callback_router.callback_query(F.data.startswith("unresolved_dismiss:"))
async def cb_unresolved_dismiss(callback: CallbackQuery):
    query_id = int(callback.data.split(":")[1])
    async with async_session_factory() as session:
        repo = KnowledgeRepository(session)
        await repo.dismiss_unresolved_query(query_id)

    await callback.answer("O'chirildi.")
    await cb_unresolved_queue(callback)


# ==========================================================
# OXIRGI MUROJAATLAR (RECENT REQUESTS)
# ==========================================================
@callback_router.callback_query(F.data == "menu:recent_messages")
async def cb_recent_messages(callback: CallbackQuery):
    async with async_session_factory() as session:
        repo = KnowledgeRepository(session)
        messages = await repo.get_recent_messages(limit=8)

    if not messages:
        await callback.answer("Hozircha xabarlar mavjud emas.", show_alert=True)
        return

    text = "📨 <b>Guruhlar va chatlardan kelgan oxirgi murojaatlar:</b>\nTafsilotini ko'rish uchun tanlang:"
    await callback.message.edit_text(text, reply_markup=get_recent_messages_keyboard(messages))
    await callback.answer()


@callback_router.callback_query(F.data.startswith("msg_view:"))
async def cb_msg_view(callback: CallbackQuery):
    msg_id = int(callback.data.split(":")[1])
    async with async_session_factory() as session:
        stmt = select(TelegramMessage).where(TelegramMessage.id == msg_id)
        res = await session.execute(stmt)
        msg = res.scalar_one_or_none()

    if not msg:
        await callback.answer("Xabar topilmadi.", show_alert=True)
        return

    text = (
        f"📨 <b>Murojaat Tafsiloti:</b>\n\n"
        f"👤 <b>Yuboruvchi:</b> {msg.sender_name or 'Noma\'lum'} (@{msg.username or '-'})\n"
        f"📅 <b>Vaqt:</b> {msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"📄 <b>Turi:</b> {msg.media_type}\n\n"
        f"💬 <b>Matn:</b>\n<i>{msg.text or '[Matnsiz media]'}</i>"
    )
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Murojaatlarga qaytish", callback_data="menu:recent_messages")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ==========================================================
# BILIMLAR BAZASI STATISTIKASI
# ==========================================================
@callback_router.callback_query(F.data == "menu:knowledge_stats")
async def cb_knowledge_stats(callback: CallbackQuery):
    async with async_session_factory() as session:
        repo = KnowledgeRepository(session)
        total_k = await repo.get_total_knowledge_count()
        today_k = await repo.get_today_learned_count()
        recent_items = await repo.get_recent_knowledge_items(limit=5)

    items_text = ""
    for idx, it in enumerate(recent_items, 1):
        items_text += f"{idx}. <b>{it.title[:35]}</b>\n   <i>{it.solution[:60]}...</i>\n"

    text = (
        f"📚 <b>Bilimlar Bazasi Statistikasi:</b>\n\n"
        f"• <b>Jami bilimlar:</b> {total_k:,} ta\n"
        f"• <b>Bugun o'rganilgan:</b> {today_k} ta\n\n"
        f"<b>So'nggi bilimlar:</b>\n{items_text if items_text else 'Hozircha bilimlar yo\'q.'}"
    )
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Bosh menyuga qaytish", callback_data="menu:refresh_settings")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


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
