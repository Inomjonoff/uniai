import asyncio
import json
import os
import sys
from sqlalchemy import text

sys.stdout.reconfigure(encoding='utf-8')

from app.db.init_db import init_database
from app.db.session import async_session_factory
from app.db.models import Knowledge, KnowledgeSource, SourceType
from app.utils.logger import logger

async def test_bulk_seed():
    await init_database()
    
    json_path = r"c:\Users\naimi\Desktop\for cv\uniai\scratch\baza_knowledge.json"
    with open(json_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    print(f"Loaded {len(items):,} items from baza_knowledge.json")

    async with async_session_factory() as session:
        print("Clearing local DB...")
        await session.execute(text("DELETE FROM knowledge_embeddings;"))
        await session.execute(text("DELETE FROM knowledge_sources;"))
        await session.execute(text("DELETE FROM attachments;"))
        await session.execute(text("DELETE FROM unresolved_queries;"))
        await session.execute(text("DELETE FROM knowledge;"))
        await session.commit()

        print("Bulk inserting knowledge records...")
        batch_size = 100
        for i in range(0, len(items), batch_size):
            batch = items[i:i+batch_size]
            for it in batch:
                full_text = f"{it['title']} {it['problem']} {it['solution']}"
                k = Knowledge(
                    title=it["title"][:490],
                    problem=it["problem"][:2000] if it.get("problem") else None,
                    possible_cause=it.get("possible_cause", "")[:1000] if it.get("possible_cause") else None,
                    solution=it["solution"],
                    raw_content=full_text,
                    category=it.get("category", "general")[:90],
                    system_name=it.get("system_name", "edo.ijro.uz")[:90],
                    confidence=1.0,
                    confidence_score=1.0,
                    trust_score=0.95,
                    verified_by_user=True,
                    is_active=True,
                    is_deleted=False,
                    tags=it.get("tags", []),
                    tags_list=it.get("tags", [])
                )
                session.add(k)
            await session.commit()
            print(f"Inserted batch {i + len(batch)}/{len(items)}")

    print("Bulk seed completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_bulk_seed())
