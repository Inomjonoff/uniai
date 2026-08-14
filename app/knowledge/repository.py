"""
Knowledge repository: database operations for knowledge, sources, embeddings, and raw messages.
"""
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import select, update, delete, and_, or_, func, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Knowledge,
    KnowledgeSource,
    KnowledgeEmbedding,
    Attachment,
    TelegramGroup,
    TelegramMessage,
    SourceType,
    TrustLevel,
    VerificationStatus,
    User,
    Feedback,
    UnresolvedQuery
)
from app.utils.logger import logger


class KnowledgeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_user_instruction(
        self,
        raw_text: str,
        user_id: int,
        sender_name: Optional[str] = None,
        embedding: Optional[List[float]] = None
    ) -> Knowledge:
        """Saves a direct user instruction with highest priority (trust_score=1.0)."""
        knowledge = Knowledge(
            title=raw_text[:100],
            problem=None,
            possible_cause=None,
            solution=raw_text,
            raw_content=raw_text,
            category="user_instruction",
            tags=["user_rule", "instruction"],
            confidence=1.0,
            trust_score=1.0,
            verification_status=VerificationStatus.VERIFIED_BY_USER,
            is_deleted=False
        )
        self.session.add(knowledge)
        await self.session.flush()

        source = KnowledgeSource(
            knowledge_id=knowledge.id,
            source_type=SourceType.USER,
            source_id=str(user_id),
            author=sender_name or f"User {user_id}",
            metadata_json={"author_id": user_id, "created_by": "direct_instruction"}
        )
        self.session.add(source)

        if embedding:
            emb_record = KnowledgeEmbedding(
                knowledge_id=knowledge.id,
                embedding=embedding,
                embedding_json=embedding,
                model_name="text-embedding-004"
            )
            self.session.add(emb_record)

        await self.session.commit()
        await self.session.refresh(knowledge)
        return knowledge

    async def save_group_knowledge(
        self,
        item: Dict[str, Any],
        chat_id: int,
        group_title: str,
        embedding: Optional[List[float]] = None
    ) -> Knowledge:
        """Saves extracted knowledge from a Telegram group."""
        knowledge = Knowledge(
            title=item.get("title") or item.get("problem", "Group knowledge")[:100],
            problem=item.get("problem"),
            possible_cause=item.get("possible_cause"),
            solution=item.get("solution"),
            raw_content=item.get("raw_content") or f"Problem: {item.get('problem')}\nSolution: {item.get('solution')}",
            category=item.get("category", "general"),
            tags=item.get("tags", []),
            confidence=float(item.get("confidence", 0.85)),
            trust_score=0.85,
            verification_status=VerificationStatus.UNVERIFIED,
            is_deleted=False
        )
        self.session.add(knowledge)
        await self.session.flush()

        source_msg_ids = item.get("source_message_ids", [])
        primary_msg_id = source_msg_ids[0] if source_msg_ids else None

        source = KnowledgeSource(
            knowledge_id=knowledge.id,
            source_type=SourceType.TELEGRAM_GROUP,
            source_id=str(chat_id),
            source_message_id=primary_msg_id,
            source_group_name=group_title,
            author=", ".join(item.get("participants", [])) if item.get("participants") else group_title,
            metadata_json={
                "all_source_message_ids": source_msg_ids,
                "participants": item.get("participants", [])
            }
        )
        self.session.add(source)

        if embedding:
            emb_record = KnowledgeEmbedding(
                knowledge_id=knowledge.id,
                embedding=embedding,
                embedding_json=embedding,
                model_name="text-embedding-004"
            )
            self.session.add(emb_record)

        await self.session.commit()
        await self.session.refresh(knowledge)
        return knowledge

    async def save_raw_telegram_message(
        self,
        message_id: int,
        chat_id: int,
        user_id: Optional[int],
        sender_name: Optional[str],
        username: Optional[str],
        text: Optional[str],
        media_type: Optional[str] = "text",
        file_id: Optional[str] = None,
        reply_to_message_id: Optional[int] = None
    ) -> TelegramMessage:
        """Stores raw message for source tracking and forwarding."""
        # Ensure group exists
        stmt = select(TelegramGroup).where(TelegramGroup.chat_id == chat_id)
        res = await self.session.execute(stmt)
        group = res.scalar_one_or_none()
        if not group:
            group = TelegramGroup(
                chat_id=chat_id,
                title="Private/Direct" if chat_id > 0 else f"Group {chat_id}",
                learning_enabled=True,
                reply_enabled=False
            )
            self.session.add(group)
            await self.session.flush()

        msg = TelegramMessage(
            message_id=message_id,
            chat_id=chat_id,
            user_id=user_id,
            sender_name=sender_name,
            username=username,
            text=text,
            media_type=media_type,
            file_id=file_id,
            reply_to_message_id=reply_to_message_id,
            is_processed=False
        )
        self.session.add(msg)
        await self.session.commit()
        return msg

    async def save_attachment(
        self,
        telegram_file_id: str,
        file_type: str,
        chat_id: Optional[int] = None,
        telegram_message_id: Optional[int] = None,
        file_name: Optional[str] = None,
        ocr_text: Optional[str] = None,
        description: Optional[str] = None,
        detected_errors: Optional[List[str]] = None,
        system_name: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        knowledge_id: Optional[int] = None
    ) -> Attachment:
        """Saves an image/document attachment record with OCR, error, and embedding metadata."""
        attachment = Attachment(
            knowledge_id=knowledge_id,
            telegram_file_id=telegram_file_id,
            telegram_message_id=telegram_message_id,
            chat_id=chat_id,
            file_name=file_name,
            file_type=file_type,
            ocr_text=ocr_text,
            description=description,
            detected_errors=detected_errors or [],
            system_name=system_name,
            embedding=embedding,
            embedding_json=embedding
        )
        self.session.add(attachment)
        await self.session.commit()
        await self.session.refresh(attachment)
        return attachment

    async def get_or_create_group(self, chat_id: int, title: str, username: Optional[str] = None) -> TelegramGroup:
        stmt = select(TelegramGroup).where(TelegramGroup.chat_id == chat_id)
        res = await self.session.execute(stmt)
        group = res.scalar_one_or_none()
        if not group:
            group = TelegramGroup(
                chat_id=chat_id,
                title=title,
                username=username,
                learning_enabled=True,
                reply_enabled=False
            )
            self.session.add(group)
            await self.session.commit()
            await self.session.refresh(group)
        else:
            if group.title != title or group.username != username:
                group.title = title
                group.username = username
                await self.session.commit()
        return group

    async def get_all_groups(self) -> List[TelegramGroup]:
        stmt = select(TelegramGroup).order_by(TelegramGroup.title)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def update_group_settings(self, chat_id: int, learning: Optional[bool] = None, reply: Optional[bool] = None) -> Optional[TelegramGroup]:
        stmt = select(TelegramGroup).where(TelegramGroup.chat_id == chat_id)
        res = await self.session.execute(stmt)
        group = res.scalar_one_or_none()
        if group:
            if learning is not None:
                group.learning_enabled = learning
            if reply is not None:
                group.reply_enabled = reply
            await self.session.commit()
            await self.session.refresh(group)
        return group

    async def get_recent_unprocessed_messages(self, chat_id: int, limit: int = 50) -> List[TelegramMessage]:
        stmt = (
            select(TelegramMessage)
            .where(and_(TelegramMessage.chat_id == chat_id, TelegramMessage.is_processed == False))
            .order_by(TelegramMessage.message_id.asc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def mark_messages_processed(self, message_ids: List[int]) -> None:
        if not message_ids:
            return
        stmt = (
            update(TelegramMessage)
            .where(TelegramMessage.id.in_(message_ids))
            .values(is_processed=True)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_today_learned_count(self) -> int:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = (
            select(func.count(Knowledge.id))
            .where(and_(Knowledge.created_at >= today_start, Knowledge.is_deleted == False))
        )
        res = await self.session.execute(stmt)
        return res.scalar_one() or 0

    async def get_total_knowledge_count(self) -> int:
        stmt = select(func.count(Knowledge.id)).where(Knowledge.is_deleted == False)
        res = await self.session.execute(stmt)
        return res.scalar_one() or 0

    async def get_recent_knowledge_items(self, limit: int = 5) -> List[Knowledge]:
        stmt = (
            select(Knowledge)
            .options(selectinload(Knowledge.sources))
            .where(Knowledge.is_deleted == False)
            .order_by(Knowledge.created_at.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def soft_delete_knowledge(self, knowledge_id: int) -> bool:
        stmt = select(Knowledge).where(Knowledge.id == knowledge_id)
        res = await self.session.execute(stmt)
        item = res.scalar_one_or_none()
        if item:
            item.is_deleted = True
            await self.session.commit()
            return True
        return False

    async def delete_all_knowledge(self) -> int:
        stmt = update(Knowledge).values(is_deleted=True)
        res = await self.session.execute(stmt)
        await self.session.commit()
        return res.rowcount or 0

    async def save_unresolved_query(
        self,
        query_text: str,
        context: Optional[str] = None,
        chat_id: Optional[int] = None,
        user_id: Optional[int] = None,
        sender_name: Optional[str] = None
    ) -> UnresolvedQuery:
        """Saves a question/issue that AI could not answer or needs learning."""
        unresolved = UnresolvedQuery(
            query_text=query_text,
            context=context,
            chat_id=chat_id,
            user_id=user_id,
            sender_name=sender_name,
            status="pending"
        )
        self.session.add(unresolved)
        await self.session.commit()
        await self.session.refresh(unresolved)
        return unresolved

    async def get_pending_unresolved_queries(self, limit: int = 20) -> List[UnresolvedQuery]:
        """Gets all unresolved topics waiting for admin review/teaching."""
        stmt = (
            select(UnresolvedQuery)
            .where(UnresolvedQuery.status == "pending")
            .order_by(UnresolvedQuery.created_at.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_unresolved_query_by_id(self, query_id: int) -> Optional[UnresolvedQuery]:
        """Gets a single unresolved query by ID."""
        stmt = select(UnresolvedQuery).where(UnresolvedQuery.id == query_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def resolve_unresolved_query(
        self,
        query_id: int,
        solution: str,
        admin_id: int,
        embedding: Optional[List[float]] = None
    ) -> Optional[Knowledge]:
        """Marks unresolved query as learned and saves solution into Knowledge base."""
        unresolved = await self.get_unresolved_query_by_id(query_id)
        if not unresolved:
            return None

        unresolved.status = "learned"
        unresolved.admin_solution = solution
        unresolved.resolved_at = datetime.utcnow()

        # Save to Knowledge Base
        knowledge = Knowledge(
            title=unresolved.query_text[:100],
            problem=unresolved.query_text,
            possible_cause=unresolved.context,
            solution=solution,
            raw_content=f"Savol: {unresolved.query_text}\nYechim: {solution}",
            category="admin_taught",
            tags=["manual_learning", "unresolved_fix"],
            confidence=1.0,
            trust_score=1.0,
            verification_status="verified_by_user",
            is_deleted=False
        )
        self.session.add(knowledge)
        await self.session.flush()

        source = KnowledgeSource(
            knowledge_id=knowledge.id,
            source_type=SourceType.USER,
            source_id=str(admin_id),
            author=f"Admin {admin_id}",
            metadata_json={"source": "unresolved_query_resolution", "query_id": query_id}
        )
        self.session.add(source)

        if embedding:
            emb_record = KnowledgeEmbedding(
                knowledge_id=knowledge.id,
                embedding=embedding,
                embedding_json=embedding,
                model_name="gemini-embedding-001"
            )
            self.session.add(emb_record)

        await self.session.commit()
        await self.session.refresh(knowledge)
        return knowledge

    async def dismiss_unresolved_query(self, query_id: int) -> bool:
        """Dismisses an unresolved query as not relevant."""
        unresolved = await self.get_unresolved_query_by_id(query_id)
        if not unresolved:
            return False
        unresolved.status = "dismissed"
        unresolved.resolved_at = datetime.utcnow()
        await self.session.commit()
        return True

    async def get_recent_messages(self, limit: int = 15) -> List[TelegramMessage]:
        """Gets recent messages across all groups for activity monitoring."""
        stmt = (
            select(TelegramMessage)
            .options(selectinload(TelegramMessage.group))
            .order_by(TelegramMessage.created_at.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
