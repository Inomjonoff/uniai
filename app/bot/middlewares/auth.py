"""
Authentication and security middleware for Telegram Bot.
Restricts private chat access to authorized admin IDs specified in ADMIN_USER_IDS.
"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from aiogram.enums import ChatType

from app.config import settings
from app.utils.logger import logger


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Check if event is from a user
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        # Handle Private Chats (Direct 1-on-1)
        if isinstance(event, Message) and event.chat.type == ChatType.PRIVATE:
            # If this is a business chat message, allow it through
            if getattr(event, "business_connection_id", None):
                return await handler(event, data)

            allowed_admins = settings.admin_ids_set
            # If ADMIN_USER_IDS is configured and current user is not in it
            if allowed_admins and user.id not in allowed_admins:
                logger.warning(f"Unauthorized private access attempt from user ID: {user.id} (@{user.username})")
                await event.answer(
                    "Kechirasiz, bu bot faqat UNICON-SOFT muhandislari uchun shaxsiy yordamchi hisoblanadi."
                )
                return

        # Handle Callback Queries in Private Chats
        if isinstance(event, CallbackQuery) and event.message and event.message.chat.type == ChatType.PRIVATE:
            allowed_admins = settings.admin_ids_set
            if allowed_admins and user.id not in allowed_admins:
                await event.answer("Ruxsat berilmagan.", show_alert=True)
                return

        # Pass to next handler
        return await handler(event, data)
