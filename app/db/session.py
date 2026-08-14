"""
Async SQLAlchemy database engine and session management.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.config import settings
from app.utils.logger import logger

Base = declarative_base()

# SQLAlchemy Async Engine
engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
    "pool_recycle": 1800,
}

# Adjust pool settings based on database URL
if "sqlite" in settings.database_url:
    engine_kwargs.pop("pool_recycle", None)
else:
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_async_engine(
    settings.database_url,
    **engine_kwargs
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency generator for FastAPI and service functions."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}", exc_info=True)
            raise
        finally:
            await session.close()
