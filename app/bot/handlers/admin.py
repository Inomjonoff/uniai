"""
Admin settings, quick buttons, and management dashboard handlers.
"""
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ChatType
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from app.db.session import async_session_factory
from app.db.models import Setting, TelegramGroup
from app.knowledge.repository import KnowledgeRepository
from app.ai.gemini_client import gemini_client
from app.bot.keyboards.inline import (
    get_settings_keyboard,
    get_group_item_keyboard,
    get_unresolved_list_keyboard,
    get_recent_messages_keyboard
)
from app.bot.keyboards.reply import get_main_reply_keyboard
from app.config import settings


class DirectInstructionState(StatesGroup):
    waiting_for_instruction = State()


admin_router = Router()
admin_router.message.filter(F.chat.type == ChatType.PRIVATE)


async def show_settings_menu(message: Message):
    """Renders the main settings and management dashboard."""
    async with async_session_factory() as session:
        repo = KnowledgeRepository(session)
        groups = await repo.get_all_groups()
        total_k = await repo.get_total_knowledge_count()
        pending_items = await repo.get_pending_unresolved_queries(limit=50)

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
        "⚙️ <b>UNICON-SOFT AI Boshqaruv Paneli</b>\n\n"
        f"• <b>Gemini AI:</b> 🟢 Faol ({settings.gemini_model})\n"
        f"• <b>Auto Learning:</b> {'🟢 ON' if auto_learn_val else '🔴 OFF'}\n"
        f"• <b>Screenshot Vision:</b> {'🟢 ON' if vision_val else '🔴 OFF'}\n"
        f"• <b>Ulangan guruhlar:</b> {len(groups)} ta\n"
        f"• <b>Bilimlar bazasi:</b> {total_k:,} ta yozuv\n"
        f"• <b>O'rganish kutilayotganlar:</b> {len(pending_items)} ta savol/muammo\n"
    )

    await message.answer(
        text,
        reply_markup=get_settings_keyboard(
            groups_count=len(groups),
            knowledge_count=total_k,
            pending_learn_count=len(pending_items),
            auto_learning=auto_learn_val,
            screenshot_analysis=vision_val
        )
    )


@admin_router.message(Command("settings"))
@admin_router.message(Command("sozlamalar"))
@admin_router.message(F.text.in_(["⚙️ Boshqaruv paneli", "⚙️ Sozlamalar"]))
async def cmd_settings(message: Message):
    await show_settings_menu(message)


@admin_router.message(Command("groups"))
@admin_router.message(Command("guruhlar"))
@admin_router.message(F.text.in_(["👥 Guruhlarni boshqarish", "👥 Guruhlar"]))
async def cmd_groups(message: Message):
    """Lists all monitored Telegram groups."""
    async with async_session_factory() as session:
        repo = KnowledgeRepository(session)
        groups = await repo.get_all_groups()

    if not groups:
        await message.answer(
            "Hozircha bot hech qanday guruhga qo'shilmagan.\n"
            "Botni texnik guruhlarga qo'shing va u avtomatik tajriba yig'ishni boshlaydi.",
            reply_markup=get_main_reply_keyboard()
        )
        return

    text = "👥 <b>Kuzatilayotgan guruhlar ro'yxati:</b>\nSozlash uchun guruhni tanlang:"
    await message.answer(text, reply_markup=get_group_item_keyboard(groups))


@admin_router.message(Command("unresolved"))
@admin_router.message(Command("organish"))
@admin_router.message(F.text.in_(["🎓 O'rganish kutilayotganlar", "🎓 O'rganish kerak"]))
async def cmd_unresolved(message: Message):
    """Shows pending unknown questions that need manual learning."""
    async with async_session_factory() as session:
        repo = KnowledgeRepository(session)
        items = await repo.get_pending_unresolved_queries(limit=20)

    if not items:
        await message.answer(
            "🎓 <b>O'rganish navbati bo'sh!</b>\nBot barcha so'ralgan texnik savollarga yechimga ega.",
            reply_markup=get_main_reply_keyboard()
        )
        return

    text = "🎓 <b>O'rganilishi kerak bo'lgan noma'lum savollar / muammolar:</b>\nYechim kiritish yoki o'chirish uchun savolni bosing:"
    await message.answer(text, reply_markup=get_unresolved_list_keyboard(items))


@admin_router.message(Command("recent"))
@admin_router.message(Command("murojaatlar"))
@admin_router.message(F.text.in_(["📨 Oxirgi murojaatlar", "📨 Murojaatlar"]))
async def cmd_recent(message: Message):
    """Shows recent requests and messages."""
    async with async_session_factory() as session:
        repo = KnowledgeRepository(session)
        messages = await repo.get_recent_messages(limit=10)

    if not messages:
        await message.answer(
            "Hozircha xabarlar tarixi mavjud emas.",
            reply_markup=get_main_reply_keyboard()
        )
        return

    text = "📨 <b>Guruhlar va chatlardan kelgan oxirgi murojaatlar:</b>"
    await message.answer(text, reply_markup=get_recent_messages_keyboard(messages))


@admin_router.message(Command("stats"))
@admin_router.message(F.text.in_(["📚 Bilimlar statistikasi", "📚 Bilimlar"]))
async def cmd_stats(message: Message):
    """Shows detailed knowledge base statistics."""
    async with async_session_factory() as session:
        repo = KnowledgeRepository(session)
        total_k = await repo.get_total_knowledge_count()
        today_k = await repo.get_today_learned_count()
        recent_items = await repo.get_recent_knowledge_items(limit=5)

    items_text = ""
    for idx, it in enumerate(recent_items, 1):
        items_text += f"{idx}. <b>{it.title[:35]}</b>\n   <i>{it.solution[:60]}...</i>\n"

    summary_list = items_text if items_text else "Hozircha bilimlar mavjud emas."

    text = (
        f"📚 <b>Bilimlar Bazasi Statistikasi:</b>\n\n"
        f"• <b>Jami bilimlar:</b> {total_k:,} ta\n"
        f"• <b>Bugun o'rganilgan:</b> {today_k} ta\n\n"
        f"<b>So'nggi o'rganilgan bilimlar:</b>\n{summary_list}"
    )
    await message.answer(text, reply_markup=get_main_reply_keyboard())


@admin_router.message(Command("topshiriq"))
@admin_router.message(Command("qoida"))
@admin_router.message(F.text.in_(["✍️ Qoida / Topshiriq berish", "✍️ Qoida o'rgatish", "✍️ Topshiriq berish"]))
async def cmd_start_teach_instruction(message: Message, state: FSMContext):
    """Starts interactive flow to teach a rule or give a task to the bot."""
    await state.set_state(DirectInstructionState.waiting_for_instruction)
    prompt_text = (
        "✍️ <b>Botga yangi topshiriq yoki qoida o'rgatish:</b>\n\n"
        "Quyida qoidani yozib yuboring.\n"
        "Masalan:\n"
        "• <i>Ijro.gov.uz da 502 chiqsa avval Nginx loglarini ko'ramiz</i>\n"
        "• <i>VPN ulanishida xatolik bo'lsa IT bo'limiga murojaat qilishni ayt</i>\n"
        "• <i>PostgreSQL parolini hech kimga bermaslik kerak</i>\n\n"
        "Marhamat, topshiriq / qoidani yozing:"
    )
    await message.answer(prompt_text)


@admin_router.message(DirectInstructionState.waiting_for_instruction, F.text)
async def handle_direct_instruction_input(message: Message, state: FSMContext):
    """Saves the direct instruction given by the admin into knowledge base."""
    instruction_text = message.text.strip()
    status_msg = await message.answer("Topshiriq saqlanmoqda va o'rganilmoqda...")

    try:
        emb = await gemini_client.generate_embedding(instruction_text)
        async with async_session_factory() as session:
            repo = KnowledgeRepository(session)
            await repo.save_user_instruction(
                raw_text=instruction_text,
                user_id=message.from_user.id,
                sender_name=message.from_user.full_name or "Admin",
                embedding=emb
            )

        await state.clear()
        import html
        escaped_instruction = html.escape(instruction_text)
        success_text = (
            f"✅ <b>Topshiriq muvaffaqiyatli eslab qolindi!</b>\n\n"
            f"📌 <b>Qoida:</b> <i>“{escaped_instruction}”</i>\n\n"
            f"Endi chatlarda yoki guruhlarda shu mavzuda savol berilsa, aynan siz bergan ushbu ko'rsatma bo'yicha javob qaytaraman."
        )
        try:
            await status_msg.edit_text(success_text, reply_markup=get_main_reply_keyboard())
        except Exception:
            await message.answer(success_text, reply_markup=get_main_reply_keyboard())
    except Exception as e:
        logger.error(f"Error saving direct instruction: {e}", exc_info=True)
        await state.clear()
        import html
        err_msg = f"Topshiriqni saqlashda xatolik bo'ldi: {html.escape(str(e))}"
        try:
            await status_msg.edit_text(err_msg, reply_markup=get_main_reply_keyboard())
        except Exception:
            await message.answer(err_msg, reply_markup=get_main_reply_keyboard())


@admin_router.message(Command("seed_knowledge"))
@admin_router.message(Command("yangilash_bazani"))
async def cmd_seed_knowledge(message: Message):
    """Wipes and re-seeds knowledge base with official mahalla.ijro.uz, edo.ijro.uz, lawyer.ijro.uz knowledge."""
    status_msg = await message.answer("🔄 Bilimlar bazasi tozalanmoqda va yangi rasmiy bilimlar yuklanmoqda...")
    try:
        from app.knowledge.seeder import seed_knowledge_base
        count = await seed_knowledge_base(clear_existing=True)
        await status_msg.edit_text(
            f"✅ <b>Bilimlar bazasi muvaffaqiyatli yangilandi!</b>\n\n"
            f"• <b>Jami yangi bilimlar:</b> {count} ta\n"
            f"• <b>Tizimlar:</b> <code>mahalla.ijro.uz</code>, <code>edo.ijro.uz</code>, <code>lawyer.ijro.uz</code>, <code>E-IMZO / DSQ</code>\n\n"
            "Endi ushbu tizimlar bo'yicha har qanday texnik muammoni bemalol so'rashingiz mumkin!",
            reply_markup=get_main_reply_keyboard()
        )
    except Exception as e:
        logger.error(f"Error seeding knowledge: {e}", exc_info=True)
        await status_msg.edit_text(f"Xatolik yuz berdi: {e}")
