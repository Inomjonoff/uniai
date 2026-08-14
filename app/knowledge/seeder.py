"""
Comprehensive knowledge seeder for UNICON-SOFT platforms:
Loads real historical technical support data extracted from Telegram group exports:
- edo.ijro.uz (Elektron hujjat aylanish tizimi va ijro intizomi)
- lawyer.ijro.uz (e-huquqshinos yuridik xizmat portali)
- mahalla.ijro.uz (Mahalla yettiligi va fuqarolar arizalari)
- E-IMZO, DSQ va OneID umumiy texnik yechimlari
"""
import os
import json
import asyncio
from typing import List, Dict, Any
from sqlalchemy import text

from app.db.session import async_session_factory
from app.db.models import Knowledge, KnowledgeSource, KnowledgeEmbedding, SourceType
from app.ai.gemini_client import gemini_client
from app.utils.logger import logger

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, "baza_knowledge.json")


async def seed_knowledge_base(clear_existing: bool = True) -> int:
    """Clears existing knowledge and seeds curated technical knowledge from baza exports."""
    logger.info("Starting knowledge base seeding from baza_knowledge.json...")

    if not os.path.exists(JSON_FILE):
        logger.error(f"Knowledge JSON file not found at: {JSON_FILE}")
        return 0

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        items: List[Dict[str, Any]] = json.load(f)

    logger.info(f"Loaded {len(items):,} items from baza_knowledge.json")

    async with async_session_factory() as session:
        if clear_existing:
            logger.info("Clearing old knowledge base records...")
            await session.execute(text("DELETE FROM knowledge_embeddings;"))
            await session.execute(text("DELETE FROM knowledge_sources;"))
            await session.execute(text("DELETE FROM attachments;"))
            await session.execute(text("DELETE FROM unresolved_queries;"))
            await session.execute(text("DELETE FROM knowledge;"))
            await session.commit()
            logger.info("Existing knowledge base wiped cleanly.")

        batch_size = 100
        inserted_count = 0

        for i in range(0, len(items), batch_size):
            batch = items[i:i+batch_size]
            for it in batch:
                title = it.get("title", "")[:490]
                problem = it.get("problem", "")[:2000] if it.get("problem") else None
                possible_cause = it.get("possible_cause", "")[:1000] if it.get("possible_cause") else None
                solution = it.get("solution", "")
                raw_content = f"{title} {problem or ''} {solution}"
                sys_name = it.get("system_name", "edo.ijro.uz")[:90]
                category = it.get("category", "foydalanuvchi_murojaati")[:90]
                tags = it.get("tags", ["baza", sys_name.split(".")[0]])

                k = Knowledge(
                    title=title,
                    problem=problem,
                    possible_cause=possible_cause,
                    solution=solution,
                    raw_content=raw_content,
                    category=category,
                    system_name=sys_name,
                    confidence=1.0,
                    confidence_score=1.0,
                    trust_score=0.95,
                    verified_by_user=True,
                    is_active=True,
                    is_deleted=False,
                    tags=tags,
                    tags_list=tags
                )
                session.add(k)
                inserted_count += 1

            await session.commit()
            logger.info(f"Seeded batch {inserted_count}/{len(items)} knowledge records.")

        logger.info(f"Knowledge base successfully seeded with {inserted_count} records!")
        return inserted_count


if __name__ == "__main__":
    asyncio.run(seed_knowledge_base(clear_existing=True))
