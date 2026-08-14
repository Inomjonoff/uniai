"""
Background tasks implementation for group message batching, knowledge extraction, and embedding.
"""
import asyncio
from typing import Dict, Any, List
from sqlalchemy import select, and_

from app.db.session import async_session_factory
from app.db.models import TelegramGroup, TelegramMessage, KnowledgeEmbedding
from app.knowledge.repository import KnowledgeRepository
from app.knowledge.deduplication import is_duplicate
from app.ai.extractor import knowledge_extractor
from app.ai.gemini_client import gemini_client
from app.workers.queue import task_queue
from app.config import settings
from app.utils.logger import logger


async def process_group_batch_task(payload: Dict[str, Any]):
    """
    Background worker task to extract and index knowledge from a Telegram group.
    """
    chat_id = payload.get("chat_id")
    group_title = payload.get("group_title", f"Group {chat_id}")

    if not chat_id:
        return

    logger.info(f"Starting background knowledge extraction for group '{group_title}' (Chat ID: {chat_id})")

    async with async_session_factory() as session:
        repo = KnowledgeRepository(session)
        
        # 1. Fetch group details
        stmt = select(TelegramGroup).where(TelegramGroup.chat_id == chat_id)
        res = await session.execute(stmt)
        group = res.scalar_one_or_none()

        if not group or not group.learning_enabled:
            logger.info(f"Learning is disabled for group '{group_title}', skipping extraction.")
            return

        # 2. Fetch unprocessed messages
        messages = await repo.get_recent_unprocessed_messages(chat_id=chat_id, limit=30)
        if not messages or len(messages) < 2:
            # Need at least some conversation to extract context
            return

        message_dicts = [
            {
                "message_id": m.message_id,
                "sender_name": m.sender_name,
                "username": m.username,
                "text": m.text,
                "media_type": m.media_type,
                "timestamp": m.timestamp
            }
            for m in messages
        ]

        # 3. Call AI extractor
        extracted_items = await knowledge_extractor.extract_from_group_messages(
            group_title=group_title,
            messages=message_dicts
        )

        if extracted_items:
            # 4. Fetch recent embeddings for deduplication
            emb_stmt = select(KnowledgeEmbedding).order_by(KnowledgeEmbedding.id.desc()).limit(100)
            emb_res = await session.execute(emb_stmt)
            existing_embeddings = [
                e.embedding_json if e.embedding_json else e.embedding
                for e in emb_res.scalars().all()
                if (e.embedding_json or e.embedding)
            ]

            saved_count = 0
            for item in extracted_items:
                raw_text = f"{item.get('problem', '')} {item.get('possible_cause', '')} {item.get('solution', '')}"
                embedding = await gemini_client.generate_embedding(raw_text)

                if not is_duplicate(embedding, existing_embeddings, threshold=settings.dedup_threshold):
                    await repo.save_group_knowledge(
                        item=item,
                        chat_id=chat_id,
                        group_title=group_title,
                        embedding=embedding
                    )
                    existing_embeddings.append(embedding)
                    saved_count += 1
                else:
                    logger.info(f"Duplicate knowledge skipped: {item.get('title')}")

            logger.info(f"Successfully indexed {saved_count} new knowledge items from '{group_title}'")

        # 5. Mark batch messages as processed
        db_message_ids = [m.id for m in messages]
        await repo.mark_messages_processed(db_message_ids)


# Register handler with queue
task_queue.register_handler("process_group_batch", process_group_batch_task)


async def periodic_group_learning_cron():
    """
    Periodic task that runs every N seconds in background to check for groups with unprocessed messages.
    """
    logger.info("Periodic group learning scanner started.")
    while True:
        try:
            await asyncio.sleep(settings.group_batch_window_seconds)
            async with async_session_factory() as session:
                # Find groups that have learning enabled
                stmt = select(TelegramGroup).where(TelegramGroup.learning_enabled == True)
                res = await session.execute(stmt)
                groups = res.scalars().all()

                for grp in groups:
                    # Check if group has unprocessed messages
                    msg_stmt = (
                        select(TelegramMessage.id)
                        .where(and_(TelegramMessage.chat_id == grp.chat_id, TelegramMessage.is_processed == False))
                        .limit(2)
                    )
                    msg_res = await session.execute(msg_stmt)
                    if len(msg_res.scalars().all()) >= 2:
                        await task_queue.enqueue(
                            "process_group_batch",
                            {"chat_id": grp.chat_id, "group_title": grp.title}
                        )
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in periodic group learning cron: {e}", exc_info=True)
            await asyncio.sleep(10)
