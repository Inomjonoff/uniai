"""
Hybrid search engine for UNICON-SOFT AI Technical Assistant.
Combines pgvector semantic search, full-text keyword matching, source trust ranking,
and original message/attachment retrieval.
"""
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import select, or_, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Knowledge,
    KnowledgeSource,
    KnowledgeEmbedding,
    TelegramMessage,
    TelegramGroup,
    Attachment,
    SourceType,
    PGVECTOR_AVAILABLE
)
from app.knowledge.deduplication import cosine_similarity
from app.ai.gemini_client import gemini_client
from app.config import settings
from app.utils.logger import logger


class HybridSearchEngine:
    def __init__(self, session: AsyncSession, client=gemini_client):
        self.session = session
        self.client = client

    async def search(
        self,
        query: str,
        limit: int = 5,
        min_score: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid search combining semantic embeddings, full-text keywords,
        and source trust weighting (USER > TELEGRAM_GROUP > FILE > WEB).
        """
        if not query or not query.strip():
            return []

        query_embedding = await self.client.generate_embedding(query)
        results: List[Dict[str, Any]] = []

        # 1. Fetch active knowledge items with their embeddings and sources
        stmt = (
            select(Knowledge)
            .options(
                selectinload(Knowledge.sources),
                selectinload(Knowledge.embeddings),
                selectinload(Knowledge.attachments)
            )
            .where(Knowledge.is_deleted == False)
        )
        res = await self.session.execute(stmt)
        all_items = res.scalars().all()

        query_terms = [t.lower() for t in query.split() if len(t) > 2]

        for item in all_items:
            # Semantic Similarity
            sem_score = 0.0
            if item.embeddings:
                emb = item.embeddings[0]
                vec = emb.embedding_json if emb.embedding_json else emb.embedding
                if vec:
                    sem_score = cosine_similarity(query_embedding, vec)

            # Keyword Match Score
            text_corpus = f"{item.title or ''} {item.problem or ''} {item.possible_cause or ''} {item.solution or ''} {item.raw_content or ''}".lower()
            keyword_matches = sum(1 for term in query_terms if term in text_corpus)
            kw_score = (keyword_matches / len(query_terms)) if query_terms else 0.0

            # Source Trust Weighting
            source_weight = 1.0
            primary_source = item.sources[0] if item.sources else None
            if primary_source:
                if primary_source.source_type == SourceType.USER:
                    source_weight = 1.35  # Strong boost for user instructions
                elif primary_source.source_type == SourceType.TELEGRAM_GROUP:
                    source_weight = 1.0
                elif primary_source.source_type == SourceType.FILE:
                    source_weight = 0.9
                elif primary_source.source_type == SourceType.WEB:
                    source_weight = 0.7

            # Combined Hybrid Score
            # 60% semantic + 40% keyword * trust multiplier
            combined_score = ((0.6 * sem_score) + (0.4 * kw_score)) * source_weight

            if combined_score >= min_score or (source_weight > 1.2 and kw_score > 0.3):
                results.append({
                    "knowledge": item,
                    "score": round(combined_score, 4),
                    "semantic_score": round(sem_score, 4),
                    "keyword_score": round(kw_score, 4),
                    "source": primary_source,
                    "attachments": item.attachments
                })

        # Sort by final score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    async def search_raw_telegram_messages(
        self,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Searches raw stored group messages for exact context or retrieval."""
        terms = [t.strip() for t in query.split() if len(t.strip()) > 2]
        if not terms:
            return []

        conditions = [TelegramMessage.text.ilike(f"%{term}%") for term in terms]
        stmt = (
            select(TelegramMessage, TelegramGroup)
            .join(TelegramGroup, TelegramGroup.chat_id == TelegramMessage.chat_id, isouter=True)
            .where(or_(*conditions))
            .order_by(TelegramMessage.timestamp.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        rows = res.all()

        results = []
        for msg, group in rows:
            results.append({
                "message_id": msg.message_id,
                "chat_id": msg.chat_id,
                "group_title": group.title if group else "Unknown Group",
                "group_username": group.username if group else None,
                "sender_name": msg.sender_name or msg.username or "Unknown",
                "text": msg.text,
                "media_type": msg.media_type,
                "file_id": msg.file_id,
                "timestamp": msg.timestamp
            })
        return results

    async def search_similar_attachments(
        self,
        query: str,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Searches screenshots or documents by OCR text or description."""
        query_embedding = await self.client.generate_embedding(query)
        stmt = select(Attachment).order_by(Attachment.created_at.desc()).limit(50)
        res = await self.session.execute(stmt)
        attachments = res.scalars().all()

        results = []
        for att in attachments:
            vec = att.embedding_json if att.embedding_json else att.embedding
            score = 0.0
            if vec:
                score = cosine_similarity(query_embedding, vec)
            
            # Text check
            text_corpus = f"{att.ocr_text or ''} {att.description or ''} {' '.join(att.detected_errors or [])}".lower()
            if any(term in text_corpus for term in query.lower().split()):
                score = max(score, 0.75)

            if score > 0.6:
                results.append({
                    "attachment": att,
                    "score": score
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
