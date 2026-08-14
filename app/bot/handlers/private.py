"""
Private chat message handlers for UNICON-SOFT AI Technical Assistant.
Handles natural dialogues, screenshots, file ingestion, and direct commands.
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, BusinessConnection
from aiogram.filters import CommandStart, Command
from aiogram.enums import ChatType
import io

from app.db.session import async_session_factory
from app.ai.agent import AssistantAgent
from app.ai.vision import vision_analyzer
from app.ai.file_processor import file_processor
from app.ai.gemini_client import gemini_client
from app.knowledge.repository import KnowledgeRepository
from app.bot.keyboards.inline import get_confirmation_keyboard, get_feedback_keyboard
from app.utils.telegram_helpers import split_message_text
from app.utils.logger import logger

private_router = Router()
# Filter for private chats only
private_router.message.filter(F.chat.type == ChatType.PRIVATE)


@private_router.message(CommandStart())
async def cmd_start(message: Message):
    """Start command handler."""
    welcome_text = (
        f"Assalomu alaykum, {message.from_user.first_name}!\n\n"
        "Men UNICON-SOFT texnik yordamchisiman. Siz bilan oddiy muloqot qilaman, "
        "texnik guruhlardan va ko'rsatmalaringizdan o'rganib boraman.\n\n"
        "Menga bemalol savol berishingiz, screenshot yoki fayl yuborishingiz, "
        "yoki biror qoidani “Eslab qol: ...” deb o'rgatishingiz mumkin."
    )
    await message.answer(welcome_text)


@private_router.message(Command("help"))
async def cmd_help(message: Message):
    """Help command handler."""
    help_text = (
        "Qanday foydalanish mumkin?\n\n"
        "• Oddiy savol bering (masalan: <i>502 chiqyapti, nima qilay?</i>)\n"
        "• Biror qoidani o'rgating (masalan: <i>Eslab qol: Ijro.gov.uzda 502 chiqsa API servisni tekshiramiz</i>)\n"
        "• Guruhdagi muhokamalarni so'rang (masalan: <i>Kecha guruhda server xatosi haqida nima deyishgandi?</i>)\n"
        "• Original xabarni so'rang (masalan: <i>O'sha xabarni tashlab ber</i>)\n"
        "• Screenshot yuboring — xatolikni tahlil qilib beraman\n"
        "• Fayl yuboring — o'rganib bazaga qo'shaman\n"
        "• /settings — guruhlar va tizim sozlamalari"
    )
    await message.answer(help_text)


@private_router.message(F.photo)
async def handle_screenshot(message: Message, bot: Bot):
    """Handles incoming screenshot/photo for vision diagnostics and storage."""
    caption = message.caption or ""
    # Highest resolution photo
    photo = message.photo[-1]

    status_msg = await message.answer("Screenshotni ko'ryapman...")
    
    try:
        # Download photo into bytes
        file_io = io.BytesIO()
        await bot.download(photo, destination=file_io)
        image_bytes = file_io.getvalue()

        # Analyze using Gemini Vision
        analysis = await vision_analyzer.analyze_screenshot(
            image_bytes=image_bytes,
            user_caption=caption
        )

        # Save attachment to database
        async with async_session_factory() as session:
            repo = KnowledgeRepository(session)
            await repo.save_attachment(
                telegram_file_id=photo.file_id,
                file_type="image",
                chat_id=message.chat.id,
                telegram_message_id=message.message_id,
                ocr_text=analysis.get("ocr_text"),
                description=analysis.get("natural_response"),
                detected_errors=analysis.get("detected_errors"),
                system_name=analysis.get("system_name"),
                embedding=analysis.get("embedding")
            )

        reply_text = analysis.get("natural_response", "Screenshot tahlil qilindi.")
        await status_msg.edit_text(reply_text, reply_markup=get_feedback_keyboard())
    except Exception as e:
        logger.error(f"Error handling screenshot: {e}", exc_info=True)
        await status_msg.edit_text("Screenshotni tahlil qilishda xatolik yuz berdi. Iltimos qaytadan urinib ko'ring.")


@private_router.message(F.document)
async def handle_document(message: Message, bot: Bot):
    """Handles incoming document (PDF, DOCX, TXT, CSV, XLSX) for knowledge ingestion."""
    doc = message.document
    file_name = doc.file_name or "document"
    status_msg = await message.answer(f"“{file_name}” faylini o'rganyapman...")

    try:
        file_io = io.BytesIO()
        await bot.download(doc, destination=file_io)
        file_bytes = file_io.getvalue()

        # Extract text and chunk
        extracted_text = file_processor.extract_text(file_bytes, file_name)
        if not extracted_text.strip():
            await status_msg.edit_text(f"“{file_name}” faylidan matn ajratib bo'lmadi yoki fayl bo'sh.")
            return

        chunks = file_processor.chunk_text(extracted_text, chunk_size=1000)
        
        async with async_session_factory() as session:
            repo = KnowledgeRepository(session)
            for idx, chunk in enumerate(chunks[:10]):  # Index top chunks
                emb = await gemini_client.generate_embedding(chunk)
                await repo.save_group_knowledge(
                    item={
                        "title": f"{file_name} (qism {idx+1})",
                        "problem": f"Fayldan olingan ma'lumot: {file_name}",
                        "solution": chunk[:300],
                        "raw_content": chunk,
                        "category": "document",
                        "tags": ["file", file_name.split(".")[-1]],
                        "confidence": 0.95
                    },
                    chat_id=message.chat.id,
                    group_title=f"File: {file_name}",
                    embedding=emb
                )

        await status_msg.edit_text(
            f"“{file_name}” fayli muvaffaqiyatli o'rganildi va bilimlar bazasiga qo'shildi ({len(chunks)} ta bo'lim)."
        )
    except Exception as e:
        logger.error(f"Error handling document: {e}", exc_info=True)
        await status_msg.edit_text(f"Faylni o'rganishda xatolik bo'ldi: {str(e)}")


from aiogram.fsm.context import FSMContext
from app.bot.handlers.callbacks import TeachKnowledgeState


@private_router.message(TeachKnowledgeState.waiting_for_solution, F.text)
async def handle_teach_solution_input(message: Message, state: FSMContext, bot: Bot):
    """Receives admin's manual solution for an unresolved knowledge item."""
    data = await state.get_data()
    query_id = data.get("query_id")
    query_text = data.get("query_text", "")
    solution_text = message.text.strip()

    status_msg = await message.answer("Yechim saqlanmoqda va o'rganilmoqda...")

    try:
        emb = await gemini_client.generate_embedding(f"{query_text} {solution_text}")
        async with async_session_factory() as session:
            repo = KnowledgeRepository(session)
            await repo.resolve_unresolved_query(
                query_id=query_id,
                solution=solution_text,
                admin_id=message.from_user.id,
                embedding=emb
            )

        await state.clear()

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎓 O'rganish navbatiga qaytish", callback_data="menu:unresolved_queue")],
            [InlineKeyboardButton(text="⚙️ Boshqaruv menyusi", callback_data="menu:refresh_settings")]
        ])

        success_text = (
            "✅ <b>Bilim muvaffaqiyatli o'rganildi va bazaga qo'shildi!</b>\n\n"
            f"• <b>Savol/Muammo:</b> <i>{query_text}</i>\n"
            f"• <b>Yechim:</b> <i>{solution_text}</i>\n\n"
            "Endi bot guruhlarda va shaxsiy chatda ushbu savol berilganda aynan shu yechimni taqdim etadi."
        )
        await status_msg.edit_text(success_text, reply_markup=kb)
    except Exception as e:
        logger.error(f"Error saving taught knowledge: {e}", exc_info=True)
        await status_msg.edit_text(f"Xatolik yuz berdi: {e}")


@private_router.message(F.text)
async def handle_private_text(message: Message, bot: Bot):
    """Processes natural language user requests in private chat."""
    user_text = message.text
    if not user_text:
        return

    # Check for settings trigger word
    if user_text.lower() in ("sozlamalar", "settings", "sozlama", "boshqaruv", "panel"):
        from app.bot.handlers.admin import show_settings_menu
        await show_settings_menu(message)
        return

    async with async_session_factory() as session:
        agent = AssistantAgent(session=session)
        sender_name = message.from_user.full_name or message.from_user.username
        
        result = await agent.process_user_message(
            telegram_user_id=message.from_user.id,
            user_text=user_text,
            sender_name=sender_name
        )

    # 1. Require destructive confirmation
    if result.get("require_confirmation"):
        action = result.get("confirmation_action", "delete_all")
        await message.answer(
            result["reply_text"],
            reply_markup=get_confirmation_keyboard(action)
        )
        return

    # 2. Forward original Telegram message if requested
    if result.get("forward_message_id") and result.get("forward_chat_id"):
        try:
            await bot.forward_message(
                chat_id=message.chat.id,
                from_chat_id=result["forward_chat_id"],
                message_id=result["forward_message_id"]
            )
        except Exception as e:
            logger.warning(f"Could not forward message directly ({e}). Sending text link.")

    # 3. Send media screenshot if requested
    if result.get("media_file_id"):
        try:
            await message.answer_photo(
                photo=result["media_file_id"],
                caption=result.get("reply_text") or "Mana o'sha screenshot 👇"
            )
            return
        except Exception as e:
            logger.warning(f"Could not send photo ({e}). Sending text reply.")

    # 4. Standard text reply
    reply_text = result.get("reply_text", "")
    if reply_text:
        chunks = split_message_text(reply_text)
        for chunk in chunks:
            await message.answer(chunk)


from aiogram.types import Message, BusinessConnection, BusinessMessagesDeleted


@private_router.business_connection()
async def handle_business_connection(connection: BusinessConnection):
    """Handles Telegram Business account secretary mode connection updates."""
    logger.info(
        f"Telegram Business Connection: user={connection.user.id}, "
        f"auth_date={connection.date}, can_reply={connection.can_reply}, is_enabled={connection.is_enabled}"
    )


@private_router.business_message()
@private_router.edited_business_message()
async def handle_business_message(message: Message, bot: Bot):
    """Handles messages received when bot operates as Secretary/Chatbot in Telegram Business."""
    user_text = message.text or message.caption or ""
    if not user_text:
        return

    # Check if message is from the business owner or an external customer
    is_owner = bool(message.from_user and message.from_user.id in settings.admin_ids_set)

    async with async_session_factory() as session:
        agent = AssistantAgent(session=session)
        sender_name = message.from_user.full_name if message.from_user else "User"
        
        result = await agent.process_user_message(
            telegram_user_id=message.from_user.id if message.from_user else 0,
            user_text=user_text,
            sender_name=sender_name
        )

    reply_text = result.get("reply_text", "")
    if reply_text:
        chunks = split_message_text(reply_text)
        for chunk in chunks:
            if message.business_connection_id:
                try:
                    await bot.send_message(
                        chat_id=message.chat.id,
                        text=chunk,
                        business_connection_id=message.business_connection_id
                    )
                except Exception as e:
                    logger.error(f"Error sending business message: {e}")
                    await message.reply(chunk)
            else:
                await message.reply(chunk)


@private_router.deleted_business_messages()
async def handle_deleted_business_messages(event: BusinessMessagesDeleted):
    """Logs deleted business messages."""
    logger.info(f"Business messages deleted in chat {event.chat.id}: {len(event.message_ids)} messages")
