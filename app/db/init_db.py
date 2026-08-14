"""
Database initialization and migration helpers.
Ensures pgvector extension and schemas are created automatically on startup.
"""
from sqlalchemy import text
from app.db.session import engine, Base, async_session_factory
from app.db.models import User, Setting
from app.config import settings
from app.utils.logger import logger


async def init_database() -> None:
    """Initializes pgvector extension and creates all database tables."""
    logger.info("Initializing database schema and extensions...")
    
    async with engine.begin() as conn:
        if "postgresql" in settings.database_url:
            try:
                logger.info("Enabling pgvector extension (CREATE EXTENSION IF NOT EXISTS vector)...")
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            except Exception as e:
                logger.warning(f"Could not initialize pgvector extension: {e}. Falling back to standard/JSON mode.")
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        logger.info("All database tables created or verified.")

    # Seed Admin Users and Default Settings
    async with async_session_factory() as session:
        try:
            for admin_id in settings.admin_ids_set:
                from sqlalchemy import select
                stmt = select(User).where(User.telegram_id == admin_id)
                res = await session.execute(stmt)
                existing_user = res.scalar_one_or_none()
                if not existing_user:
                    new_admin = User(
                        telegram_id=admin_id,
                        full_name=f"Admin {admin_id}",
                        is_admin=True,
                        is_active=True
                    )
                    session.add(new_admin)
            
            # Default settings
            settings_defaults = [
                ("auto_learning", True, "Global automatic group learning toggle"),
                ("screenshot_analysis", True, "Enable Gemini Vision screenshot analysis"),
                ("confidence_threshold", 0.75, "Minimum confidence to index extracted knowledge"),
            ]
            for key, val, desc in settings_defaults:
                stmt = select(Setting).where(Setting.key == key)
                res = await session.execute(stmt)
                if not res.scalar_one_or_none():
                    session.add(Setting(key=key, value_json=val, description=desc))
            
            await session.commit()
            logger.info("Database seeding completed successfully.")
        except Exception as e:
            await session.rollback()
            logger.error(f"Error seeding database: {e}")
