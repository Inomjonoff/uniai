"""
Unit tests for AssistantAgent and Intent Routing.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.session import Base
from app.db.models import User, Knowledge, SourceType
from app.ai.agent import AssistantAgent
from app.ai.gemini_client import GeminiClient


@pytest_asyncio.fixture
async def test_session():
    """Provides an in-memory SQLite async database session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def mock_gemini_client():
    client = MagicMock(spec=GeminiClient)
    client.generate_text = AsyncMock(return_value="Avval API servisni tekshirib ko'ring. Siz oldin shu holatda shundan boshlashimizni aytgandingiz.")
    client.generate_embedding = AsyncMock(return_value=[0.1] * 768)
    client.parse_json_response = GeminiClient.parse_json_response
    return client


@pytest.mark.asyncio
async def test_fast_intent_detection(test_session, mock_gemini_client):
    agent = AssistantAgent(session=test_session, client=mock_gemini_client)

    # 1. Test "Eslab qol"
    intent_save = await agent.detect_intent("Eslab qol: Ijro.gov.uzda 502 chiqsa API servisni tekshiramiz.")
    assert intent_save["intent"] == "SAVE_INSTRUCTION"
    assert "Ijro.gov.uzda 502" in intent_save["instruction_text"]

    # 2. Test "Buni o'chir"
    intent_del = await agent.detect_intent("Buni o'chir")
    assert intent_del["intent"] == "DELETE_KNOWLEDGE"
    assert intent_del["is_destructive"] is False

    # 3. Test "Hamma ma'lumotlarni o'chir"
    intent_del_all = await agent.detect_intent("Hamma ma'lumotlarni o'chir")
    assert intent_del_all["intent"] == "DELETE_KNOWLEDGE"
    assert intent_del_all["is_destructive"] is True

    # 4. Test "O'sha xabarni tashlab ber"
    intent_get = await agent.detect_intent("O'sha xabarni tashlab ber")
    assert intent_get["intent"] == "RETRIEVE_ORIGINAL"

    # 5. Test "Bugun nimalarni o'rganding?"
    intent_stats = await agent.detect_intent("Bugun nimalarni o'rganding?")
    assert intent_stats["intent"] == "GET_LEARNED_STATS"


@pytest.mark.asyncio
async def test_save_instruction_flow(test_session, mock_gemini_client):
    agent = AssistantAgent(session=test_session, client=mock_gemini_client)

    user_id = 999111
    result = await agent.process_user_message(
        telegram_user_id=user_id,
        user_text="Eslab qol: 502 chiqsa avval Nginx loglarini ko'ramiz.",
        sender_name="Senior Engineer"
    )

    assert "Topshiriq / Qoida eslab qolindi" in result["reply_text"]

    # Check knowledge base
    from sqlalchemy import select
    stmt = select(Knowledge)
    res = await test_session.execute(stmt)
    saved_items = res.scalars().all()
    assert len(saved_items) == 1
    assert "502 chiqsa avval Nginx" in saved_items[0].raw_content
    assert saved_items[0].trust_score == 1.0


@pytest.mark.asyncio
async def test_destructive_delete_requires_confirmation(test_session, mock_gemini_client):
    agent = AssistantAgent(session=test_session, client=mock_gemini_client)

    user_id = 999111
    result = await agent.process_user_message(
        telegram_user_id=user_id,
        user_text="Barcha ma'lumotlarni bazadan tozalab tashla",
        sender_name="Admin"
    )

    assert result["require_confirmation"] is True
    assert result["confirmation_action"] == "delete_all"
    assert "tasdiqlaysizmi" in result["reply_text"]
