"""
Tests for Unresolved Knowledge Queue and Interactive Admin Teaching Flow.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.db.models import UnresolvedQuery
from app.knowledge.repository import KnowledgeRepository
from app.ai.gemini_client import GeminiClient


@pytest.mark.asyncio
async def test_unresolved_query_lifecycle(test_session):
    repo = KnowledgeRepository(test_session)

    # 1. Save Unresolved Query
    item = await repo.save_unresolved_query(
        query_text="Ijro.gov.uz tizimida 504 Gateway Timeout xatosi nima?",
        context="User asked in group without answer",
        chat_id=-100999,
        user_id=1487048087,
        sender_name="Engineer"
    )
    assert item.id is not None
    assert item.status == "pending"

    # 2. Query Pending Items
    pending = await repo.get_pending_unresolved_queries()
    assert len(pending) == 1
    assert pending[0].id == item.id

    # 3. Admin Teaches Solution
    synthetic_emb = [0.1] * 768
    learned_knowledge = await repo.resolve_unresolved_query(
        query_id=item.id,
        solution="504 xatosi bo'lganda timeout parametrini 60s dan 120s ga ko'tarish kerak.",
        admin_id=1487048087,
        embedding=synthetic_emb
    )

    assert learned_knowledge is not None
    assert "timeout parametrini" in learned_knowledge.solution

    # 4. Check that pending queue is now empty
    pending_after = await repo.get_pending_unresolved_queries()
    assert len(pending_after) == 0


@pytest.mark.asyncio
async def test_unresolved_dismiss_flow(test_session):
    repo = KnowledgeRepository(test_session)

    item = await repo.save_unresolved_query(
        query_text="Bugun ob-havo qanday?",
        context="Non-technical question"
    )

    dismissed = await repo.dismiss_unresolved_query(item.id)
    assert dismissed is True

    pending = await repo.get_pending_unresolved_queries()
    assert len(pending) == 0
