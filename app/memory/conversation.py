"""
Conversation memory manager for multi-turn dialogues.
Maintains history for users in private chats.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Conversation, ConversationMessage, User
from app.config import settings
from app.utils.logger import logger


class ConversationMemoryManager:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_active_conversation(self, telegram_user_id: int) -> Conversation:
        """Finds or creates an active conversation for the given Telegram user."""
        # Ensure user exists
        stmt = select(User).where(User.telegram_id == telegram_user_id)
        res = await self.session.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            user = User(
                telegram_id=telegram_user_id,
                full_name=f"User {telegram_user_id}",
                is_admin=telegram_user_id in settings.admin_ids_set,
                is_active=True
            )
            self.session.add(user)
            await self.session.flush()

        stmt_conv = (
            select(Conversation)
            .where(and_(Conversation.telegram_user_id == telegram_user_id, Conversation.is_active == True))
            .order_by(Conversation.updated_at.desc())
        )
        res_conv = await self.session.execute(stmt_conv)
        conv = res_conv.scalar_one_or_none()

        if not conv:
            conv = Conversation(
                telegram_user_id=telegram_user_id,
                title="Active Session",
                is_active=True
            )
            self.session.add(conv)
            await self.session.commit()
            await self.session.refresh(conv)

        return conv

    async def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        metadata_json: Optional[Dict[str, Any]] = None
    ) -> ConversationMessage:
        """Appends a new turn message to the conversation history."""
        msg = ConversationMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata_json=metadata_json or {}
        )
        self.session.add(msg)
        await self.session.commit()
        return msg

    async def get_recent_history(
        self,
        conversation_id: int,
        limit: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Retrieves recent conversation messages formatted for Gemini context.
        Returns list of {"role": "user"|"model"|"system", "content": "..."}
        """
        max_msgs = limit or settings.max_memory_messages
        stmt = (
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.id.desc())
            .limit(max_msgs)
        )
        res = await self.session.execute(stmt)
        messages = list(res.scalars().all())
        messages.reverse()  # Chronological order

        history = []
        for m in messages:
            # Map roles for standard LLM context
            gemini_role = "user" if m.role == "user" else "model"
            history.append({
                "role": gemini_role,
                "content": m.content
            })
        return history

    async def clear_history(self, telegram_user_id: int) -> None:
        """Deactivates current active conversation."""
        stmt = (
            select(Conversation)
            .where(and_(Conversation.telegram_user_id == telegram_user_id, Conversation.is_active == True))
        )
        res = await self.session.execute(stmt)
        for conv in res.scalars().all():
            conv.is_active = False
        await self.session.commit()
