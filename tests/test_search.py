"""
Unit tests for Hybrid Search Engine and Vector Deduplication.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.db.session import Base
from app.knowledge.repository import KnowledgeRepository
from app.knowledge.search import HybridSearchEngine
from app.knowledge.deduplication import cosine_similarity, is_duplicate
from app.ai.gemini_client import GeminiClient


@pytest_asyncio.fixture
async def test_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session

    await engine.dispose()


def test_cosine_similarity_math():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert pytest.approx(cosine_similarity(v1, v2), 0.001) == 1.0

    v3 = [0.0, 1.0, 0.0]
    assert pytest.approx(cosine_similarity(v1, v3), 0.001) == 0.0

    assert is_duplicate([1.0, 0.0, 0.0], [[0.99, 0.01, 0.0]], threshold=0.95) is True
    assert is_duplicate([1.0, 0.0, 0.0], [[0.0, 1.0, 0.0]], threshold=0.95) is False


@pytest.mark.asyncio
async def test_hybrid_search_prioritizes_user_instruction(test_session):
    mock_client = MagicMock(spec=GeminiClient)
    # Return synthetic embedding
    mock_client.generate_embedding = AsyncMock(return_value=[0.5] * 768)

    repo = KnowledgeRepository(test_session)

    # 1. Save Group Knowledge
    await repo.save_group_knowledge(
        item={
            "title": "General Nginx 502 fix",
            "problem": "502 Bad Gateway",
            "solution": "Nginx config faylini tekshirish",
            "raw_content": "Nginx 502 xatosi va proxy_pass",
            "confidence": 0.8
        },
        chat_id=-100123456,
        group_title="Devs Group",
        embedding=[0.5] * 768
    )

    # 2. Save User Instruction
    await repo.save_user_instruction(
        raw_text="Ijro.gov.uzda 502 chiqsa avval API servisni tekshiramiz.",
        user_id=12345,
        sender_name="Lead",
        embedding=[0.5] * 768
    )

    search_engine = HybridSearchEngine(session=test_session, client=mock_client)
    results = await search_engine.search("502 chiqsa nima qilay?", limit=2)

    assert len(results) == 2
    # First result should be the USER instruction due to trust weighting
    top_item = results[0]["knowledge"]
    assert "Ijro.gov.uzda 502" in top_item.raw_content
    assert results[0]["source"].source_type.value == "USER"
