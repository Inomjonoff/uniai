"""
Database schema sync script for PostgreSQL on Render.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://unicon_user:8X1mN6ZzLhWqR9tY3vB5@dpg-d9vbvde7bikc73d5tm50-a.oregon-postgres.render.com/unicon_ai_db?ssl=require"


async def main():
    engine = create_async_engine(DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        # 1. Knowledge table columns
        await conn.execute(text("ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS system_name VARCHAR(100);"))
        await conn.execute(text("ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS possible_cause TEXT;"))
        await conn.execute(text("ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS confidence_score FLOAT DEFAULT 1.0;"))
        await conn.execute(text("ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS trust_score FLOAT DEFAULT 0.8;"))
        await conn.execute(text("ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS verified_by_user BOOLEAN DEFAULT FALSE;"))

        # Create verificationstatus type safely
        await conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE verificationstatus AS ENUM ('verified_by_user', 'unverified');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        await conn.execute(text("ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS verification_status verificationstatus DEFAULT 'unverified';"))
        await conn.execute(text("ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;"))
        await conn.execute(text("ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS tags JSON DEFAULT '[]'::json;"))
        await conn.execute(text("ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS tags_list JSON DEFAULT '[]'::json;"))

        # 2. Knowledge Source columns
        await conn.execute(text("ALTER TABLE knowledge_sources ADD COLUMN IF NOT EXISTS source_id VARCHAR(255);"))
        await conn.execute(text("ALTER TABLE knowledge_sources ADD COLUMN IF NOT EXISTS source_message_id BIGINT;"))
        await conn.execute(text("ALTER TABLE knowledge_sources ADD COLUMN IF NOT EXISTS author VARCHAR(255);"))
        await conn.execute(text("ALTER TABLE knowledge_sources ADD COLUMN IF NOT EXISTS author_name VARCHAR(255);"))
        await conn.execute(text("ALTER TABLE knowledge_sources ADD COLUMN IF NOT EXISTS source_group_name VARCHAR(255);"))
        await conn.execute(text("ALTER TABLE knowledge_sources ADD COLUMN IF NOT EXISTS group_title VARCHAR(255);"))
        await conn.execute(text("ALTER TABLE knowledge_sources ADD COLUMN IF NOT EXISTS message_link VARCHAR(500);"))
        await conn.execute(text("ALTER TABLE knowledge_sources ADD COLUMN IF NOT EXISTS metadata_json JSON DEFAULT '{}'::json;"))

        # 3. Knowledge Embedding columns
        await conn.execute(text("ALTER TABLE knowledge_embeddings ADD COLUMN IF NOT EXISTS embedding JSON;"))
        await conn.execute(text("ALTER TABLE knowledge_embeddings ADD COLUMN IF NOT EXISTS embedding_json JSON;"))
        await conn.execute(text("ALTER TABLE knowledge_embeddings ADD COLUMN IF NOT EXISTS model_name VARCHAR(100) DEFAULT 'gemini-embedding-001';"))

        # 4. User table
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();"))

        # 5. Telegram Group table
        await conn.execute(text("ALTER TABLE telegram_groups ADD COLUMN IF NOT EXISTS reply_enabled BOOLEAN DEFAULT FALSE;"))
        await conn.execute(text("ALTER TABLE telegram_groups ADD COLUMN IF NOT EXISTS learning_enabled BOOLEAN DEFAULT TRUE;"))

        # 6. Unresolved queries table
        await conn.execute(text("""
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
        """))

    print(">>> All PostgreSQL tables and columns successfully migrated and synced!")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
