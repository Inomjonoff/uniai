"""
Global test fixtures for pytest suite.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.session import Base
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
    client.generate_text = AsyncMock(return_value="Salom! Sizga qanday yordam bera olaman?")
    client.generate_embedding = AsyncMock(return_value=[0.1] * 768)
    client.parse_json_response = MagicMock(side_effect=lambda x: None)
    return client
