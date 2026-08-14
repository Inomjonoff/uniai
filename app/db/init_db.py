"""
Database initialization and comprehensive migration helpers.
Ensures pgvector extension, schemas, and all columns are created automatically on startup.
"""
from sqlalchemy import text
from app.db.session import engine, Base, async_session_factory
from app.db.models import User, Setting
from app.config import settings
from app.utils.logger import logger


async def init_database() -> None:
    """Initializes pgvector extension and creates/migrates all database tables."""
    logger.info("Initializing database schema and extensions...")
    
    async with engine.begin() as conn:
        if "postgresql" in settings.database_url:
            try:
                logger.info("Enabling pgvector extension (CREATE EXTENSION IF NOT EXISTS vector)...")
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            except Exception as e:
                logger.warning(f"Could not initialize pgvector extension: {e}. Falling back to standard/JSON mode.")
        
        # Create all tables if not existing
        await conn.run_sync(Base.metadata.create_all)
        logger.info("All database tables created or verified.")

    # Migrate existing PostgreSQL tables with newly added columns (one by one in isolated transactions)
    if "postgresql" in settings.database_url:
        migration_statements = [
            # 1. knowledge
            "ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS system_name VARCHAR(100);",
            "ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS problem TEXT;",
            "ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS possible_cause TEXT;",
            "ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS raw_content TEXT;",
            "ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS category VARCHAR(100) DEFAULT 'general';",
            "ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS confidence FLOAT DEFAULT 1.0;",
            "ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS confidence_score FLOAT DEFAULT 1.0;",
            "ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS trust_score FLOAT DEFAULT 0.8;",
            "ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS verified_by_user BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
            "ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS tags JSON DEFAULT '[]'::json;",
            "ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS tags_list JSON DEFAULT '[]'::json;",
            "ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();",
            "ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();",

            # 2. knowledge_sources
            "ALTER TABLE knowledge_sources ADD COLUMN IF NOT EXISTS source_id VARCHAR(255);",
            "ALTER TABLE knowledge_sources ADD COLUMN IF NOT EXISTS source_message_id BIGINT;",
            "ALTER TABLE knowledge_sources ADD COLUMN IF NOT EXISTS author VARCHAR(255);",
            "ALTER TABLE knowledge_sources ADD COLUMN IF NOT EXISTS author_name VARCHAR(255);",
            "ALTER TABLE knowledge_sources ADD COLUMN IF NOT EXISTS source_group_name VARCHAR(255);",
            "ALTER TABLE knowledge_sources ADD COLUMN IF NOT EXISTS group_title VARCHAR(255);",
            "ALTER TABLE knowledge_sources ADD COLUMN IF NOT EXISTS message_link VARCHAR(500);",
            "ALTER TABLE knowledge_sources ADD COLUMN IF NOT EXISTS metadata_json JSON DEFAULT '{}'::json;",
            "ALTER TABLE knowledge_sources ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();",

            # 3. knowledge_embeddings
            "ALTER TABLE knowledge_embeddings ADD COLUMN IF NOT EXISTS embedding JSON;",
            "ALTER TABLE knowledge_embeddings ADD COLUMN IF NOT EXISTS embedding_json JSON;",
            "ALTER TABLE knowledge_embeddings ADD COLUMN IF NOT EXISTS model_name VARCHAR(100) DEFAULT 'gemini-embedding-001';",
            "ALTER TABLE knowledge_embeddings ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();",

            # 4. users
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(100);",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255);",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();",

            # 5. telegram_groups
            "ALTER TABLE telegram_groups ADD COLUMN IF NOT EXISTS username VARCHAR(100);",
            "ALTER TABLE telegram_groups ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
            "ALTER TABLE telegram_groups ADD COLUMN IF NOT EXISTS reply_enabled BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE telegram_groups ADD COLUMN IF NOT EXISTS learning_enabled BOOLEAN DEFAULT TRUE;",
            "ALTER TABLE telegram_groups ADD COLUMN IF NOT EXISTS last_sync_at TIMESTAMP;",
            "ALTER TABLE telegram_groups ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();",

            # 6. telegram_messages
            "ALTER TABLE telegram_messages ADD COLUMN IF NOT EXISTS user_id BIGINT;",
            "ALTER TABLE telegram_messages ADD COLUMN IF NOT EXISTS sender_name VARCHAR(255);",
            "ALTER TABLE telegram_messages ADD COLUMN IF NOT EXISTS username VARCHAR(100);",
            "ALTER TABLE telegram_messages ADD COLUMN IF NOT EXISTS text TEXT;",
            "ALTER TABLE telegram_messages ADD COLUMN IF NOT EXISTS media_type VARCHAR(50) DEFAULT 'text';",
            "ALTER TABLE telegram_messages ADD COLUMN IF NOT EXISTS file_id VARCHAR(255);",
            "ALTER TABLE telegram_messages ADD COLUMN IF NOT EXISTS reply_to_message_id BIGINT;",
            "ALTER TABLE telegram_messages ADD COLUMN IF NOT EXISTS is_processed BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE telegram_messages ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();",

            # 7. unresolved_queries
            """
            CREATE TABLE IF NOT EXISTS unresolved_queries (
                id SERIAL PRIMARY KEY,
                query_text TEXT NOT NULL,
                context TEXT,
                chat_id BIGINT,
                user_id BIGINT,
                sender_name VARCHAR(255),
                status VARCHAR(50) DEFAULT 'pending' NOT NULL,
                created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                resolved_at TIMESTAMP
            );
            """,
            "ALTER TABLE unresolved_queries ADD COLUMN IF NOT EXISTS admin_solution TEXT;"
        ]
        for stmt in migration_statements:
            try:
                async with engine.begin() as conn:
                    await conn.execute(text(stmt))
            except Exception as me:
                logger.debug(f"Migration note ({stmt.strip()[:40]}): {me}")
        logger.info("Comprehensive database schema columns synchronized successfully.")

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
