"""
Database initialization and comprehensive migration helpers.
Ensures pgvector extension, schemas, and all columns are created/migrated automatically on startup for both SQLite and PostgreSQL.
"""
from sqlalchemy import text
from app.db.session import engine, Base, async_session_factory
from app.db.models import User, Setting
from app.config import settings
from app.utils.logger import logger


async def init_database() -> None:
    """Initializes pgvector extension and creates/migrates all database tables."""
    logger.info("Initializing database schema and extensions...")
    
    is_postgres = "postgresql" in settings.database_url

    async with engine.begin() as conn:
        if is_postgres:
            try:
                logger.info("Enabling pgvector extension (CREATE EXTENSION IF NOT EXISTS vector)...")
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            except Exception as e:
                logger.warning(f"Could not initialize pgvector extension: {e}. Falling back to standard/JSON mode.")
        
        # Create all tables if not existing
        await conn.run_sync(Base.metadata.create_all)
        logger.info("All database tables created or verified.")

    # Fix any legacy column types on PostgreSQL to universal types (JSON/VARCHAR)
    if is_postgres:
        conversions = [
            "ALTER TABLE knowledge DROP COLUMN IF EXISTS verification_status CASCADE;",
            "ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS verification_status VARCHAR(50) DEFAULT 'unverified';",
            "ALTER TABLE knowledge DROP COLUMN IF EXISTS trust_level CASCADE;",
            "ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS trust_level VARCHAR(50) DEFAULT 'TELEGRAM_GROUP';",
            "ALTER TABLE knowledge_embeddings DROP COLUMN IF EXISTS embedding CASCADE;",
            "ALTER TABLE knowledge_embeddings ADD COLUMN IF NOT EXISTS embedding JSON;",
            "ALTER TABLE attachments DROP COLUMN IF EXISTS embedding CASCADE;",
            "ALTER TABLE attachments ADD COLUMN IF NOT EXISTS embedding JSON;"
        ]
        for stmt in conversions:
            try:
                async with engine.begin() as conn:
                    await conn.execute(text(stmt))
            except Exception as e:
                logger.debug(f"Conversion note: {e}")

    # Universal column migrations (works on both PostgreSQL and SQLite)
    migration_columns = [
        # table, column, type_and_default
        ("knowledge", "system_name", "VARCHAR(100)"),
        ("knowledge", "problem", "TEXT"),
        ("knowledge", "possible_cause", "TEXT"),
        ("knowledge", "raw_content", "TEXT"),
        ("knowledge", "category", "VARCHAR(100) DEFAULT 'general'"),
        ("knowledge", "confidence", "FLOAT DEFAULT 1.0"),
        ("knowledge", "confidence_score", "FLOAT DEFAULT 1.0"),
        ("knowledge", "trust_score", "FLOAT DEFAULT 0.8"),
        ("knowledge", "trust_level", "VARCHAR(50) DEFAULT 'TELEGRAM_GROUP'"),
        ("knowledge", "verified_by_user", "BOOLEAN DEFAULT FALSE"),
        ("knowledge", "verification_status", "VARCHAR(50) DEFAULT 'unverified'"),
        ("knowledge", "is_active", "BOOLEAN DEFAULT TRUE"),
        ("knowledge", "is_deleted", "BOOLEAN DEFAULT FALSE"),
        ("knowledge", "tags", "JSON DEFAULT '[]'"),
        ("knowledge", "tags_list", "JSON DEFAULT '[]'"),
        ("knowledge", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("knowledge", "updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("knowledge_sources", "source_id", "VARCHAR(255)"),
        ("knowledge_sources", "source_message_id", "BIGINT"),
        ("knowledge_sources", "chat_id", "BIGINT"),
        ("knowledge_sources", "message_id", "BIGINT"),
        ("knowledge_sources", "author", "VARCHAR(255)"),
        ("knowledge_sources", "author_name", "VARCHAR(255)"),
        ("knowledge_sources", "source_group_name", "VARCHAR(255)"),
        ("knowledge_sources", "group_title", "VARCHAR(255)"),
        ("knowledge_sources", "message_link", "VARCHAR(500)"),
        ("knowledge_sources", "metadata_json", "JSON DEFAULT '{}'"),
        ("knowledge_sources", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("knowledge_embeddings", "embedding", "JSON"),
        ("knowledge_embeddings", "embedding_json", "JSON"),
        ("knowledge_embeddings", "model_name", "VARCHAR(100) DEFAULT 'gemini-embedding-001'"),
        ("knowledge_embeddings", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("users", "username", "VARCHAR(100)"),
        ("users", "full_name", "VARCHAR(255)"),
        ("users", "is_admin", "BOOLEAN DEFAULT FALSE"),
        ("users", "is_active", "BOOLEAN DEFAULT TRUE"),
        ("users", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("users", "updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("telegram_groups", "username", "VARCHAR(100)"),
        ("telegram_groups", "is_active", "BOOLEAN DEFAULT TRUE"),
        ("telegram_groups", "reply_enabled", "BOOLEAN DEFAULT FALSE"),
        ("telegram_groups", "learning_enabled", "BOOLEAN DEFAULT TRUE"),
        ("telegram_groups", "last_sync_at", "TIMESTAMP"),
        ("telegram_groups", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("telegram_messages", "user_id", "BIGINT"),
        ("telegram_messages", "sender_name", "VARCHAR(255)"),
        ("telegram_messages", "username", "VARCHAR(100)"),
        ("telegram_messages", "text", "TEXT"),
        ("telegram_messages", "media_type", "VARCHAR(50) DEFAULT 'text'"),
        ("telegram_messages", "file_id", "VARCHAR(255)"),
        ("telegram_messages", "reply_to_message_id", "BIGINT"),
        ("telegram_messages", "is_processed", "BOOLEAN DEFAULT FALSE"),
        ("telegram_messages", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("unresolved_queries", "admin_solution", "TEXT")
    ]

    for table, col, col_type in migration_columns:
        stmt_str = f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_type};" if is_postgres else f"ALTER TABLE {table} ADD COLUMN {col} {col_type};"
        try:
            async with engine.begin() as conn:
                await conn.execute(text(stmt_str))
        except Exception:
            # Column already exists or table is being created
            pass

    logger.info("Database schema columns migrated successfully.")

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
