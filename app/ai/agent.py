"""
Central AI Agent and Intent Router for UNICON-SOFT Technical Assistant.
Translates natural language user requests into tool actions and responses.
"""
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
import re
from datetime import datetime, timedelta

from app.ai.gemini_client import gemini_client
from app.ai.prompts import (
    SYSTEM_ASSISTANT_PROMPT,
    INTENT_DETECTION_PROMPT
)
from app.knowledge.repository import KnowledgeRepository
from app.knowledge.search import HybridSearchEngine
from app.memory.conversation import ConversationMemoryManager
from app.utils.telegram_helpers import make_telegram_message_link
from app.utils.logger import logger


class AssistantAgent:
    def __init__(self, session: AsyncSession, client=gemini_client):
        self.session = session
        self.client = client
        self.repo = KnowledgeRepository(session)
        self.search_engine = HybridSearchEngine(session, client)
        self.memory = ConversationMemoryManager(session)

    async def detect_intent(self, user_text: str) -> Dict[str, Any]:
        """Classifies the natural language intent of the user."""
        text_lower = user_text.lower().strip()

        # Fast heuristic checks for common Uzbek conversational commands
        if text_lower.startswith(("eslab qol", "yodda tut", "buni eslab qol", "buni saqla", "saqlab qo'y")):
            clean_instruction = re.sub(r"^(eslab qol:?|yodda tut:?|buni eslab qol:?|buni saqla:?|saqlab qo'y:?)\s*", "", user_text, flags=re.IGNORECASE).strip()
            return {
                "intent": "SAVE_INSTRUCTION",
                "instruction_text": clean_instruction or user_text,
                "search_query": "",
                "is_destructive": False
            }

        if any(w in text_lower for w in ["o'chir", "ochir", "tozala", "esdan chiqar"]):
            is_destructive = any(w in text_lower for w in ["hamma", "barcha", "butun", "bazani"])
            return {
                "intent": "DELETE_KNOWLEDGE",
                "instruction_text": "",
                "search_query": text_lower,
                "is_destructive": is_destructive
            }

        if any(w in text_lower for w in ["tashlab ber", "tashla", "forward qil", "linkini ber", "o'sha xabarni"]):
            return {
                "intent": "RETRIEVE_ORIGINAL",
                "instruction_text": "",
                "search_query": text_lower,
                "is_destructive": False
            }

        if any(w in text_lower for w in ["nimalarni o'rganding", "nima o'rganding", "bugun nima bo'ldi", "statistik"]):
            return {
                "intent": "GET_LEARNED_STATS",
                "instruction_text": "",
                "search_query": "",
                "is_destructive": False
            }

        # Fallback to Gemini intent classification for complex queries
        prompt = f"Foydalanuvchi xabari: \"{user_text}\""
        raw_intent = await self.client.generate_text(
            prompt=prompt,
            system_instruction=INTENT_DETECTION_PROMPT,
            temperature=0.0,
            json_output=True
        )
        parsed = self.client.parse_json_response(raw_intent)
        if isinstance(parsed, dict) and "intent" in parsed:
            return parsed

        return {
            "intent": "GENERAL_CHAT",
            "instruction_text": "",
            "search_query": user_text,
            "is_destructive": False
        }

    async def process_user_message(
        self,
        telegram_user_id: int,
        user_text: str,
        sender_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for processing a private message from an engineer/admin.
        Returns response dictionary: {"reply_text": str, "require_confirmation": bool, "forward_message": ...}
        """
        # 1. Manage Conversation Context
        conv = await self.memory.get_or_create_active_conversation(telegram_user_id)
        history = await self.memory.get_recent_history(conv.id)

        # 2. Detect Intent
        intent_info = await self.detect_intent(user_text)
        intent = intent_info.get("intent", "GENERAL_CHAT")
        logger.info(f"User {telegram_user_id} intent: {intent} | Text: {user_text[:80]}")

        response_payload = {
            "reply_text": "",
            "require_confirmation": False,
            "confirmation_action": None,
            "confirmation_data": None,
            "forward_message_id": None,
            "forward_chat_id": None,
            "media_file_id": None
        }

        # ==========================================================
        # INTENT: SAVE_INSTRUCTION
        # ==========================================================
        if intent == "SAVE_INSTRUCTION":
            instruction = intent_info.get("instruction_text") or user_text
            emb = await self.client.generate_embedding(instruction)
            await self.repo.save_user_instruction(
                raw_text=instruction,
                user_id=telegram_user_id,
                sender_name=sender_name,
                embedding=emb
            )
            reply = "Xo'p, eslab qoldim."
            response_payload["reply_text"] = reply
            await self.memory.add_message(conv.id, "user", user_text)
            await self.memory.add_message(conv.id, "assistant", reply)
            return response_payload

        # ==========================================================
        # INTENT: DELETE_KNOWLEDGE
        # ==========================================================
        if intent == "DELETE_KNOWLEDGE":
            if intent_info.get("is_destructive"):
                total = await self.repo.get_total_knowledge_count()
                response_payload["require_confirmation"] = True
                response_payload["confirmation_action"] = "delete_all"
                response_payload["reply_text"] = f"{total:,} ta bilim yozuvi o'chiriladi. Haqiqatan barcha bilimlarni o'chirishni tasdiqlaysizmi?"
                return response_payload
            else:
                # Soft delete most recent knowledge or search for specified
                recent = await self.repo.get_recent_knowledge_items(limit=1)
                if recent:
                    item = recent[0]
                    await self.repo.soft_delete_knowledge(item.id)
                    reply = f"Oxirgi saqlangan ma'lumot (\"{item.title or item.raw_content[:40]}...\") o'chirildi."
                else:
                    reply = "O'chirish uchun biror ma'lumot topilmadi."
                response_payload["reply_text"] = reply
                await self.memory.add_message(conv.id, "user", user_text)
                await self.memory.add_message(conv.id, "assistant", reply)
                return response_payload

        # ==========================================================
        # INTENT: GET_LEARNED_STATS
        # ==========================================================
        if intent == "GET_LEARNED_STATS":
            today_count = await self.repo.get_today_learned_count()
            total_count = await self.repo.get_total_knowledge_count()
            recent_items = await self.repo.get_recent_knowledge_items(limit=3)

            if today_count == 0 and total_count == 0:
                reply = "Hozircha yangi bilimlar yozilmagan. Guruhlarni kuzatishda davom etyapman."
            else:
                items_summary = []
                for it in recent_items:
                    items_summary.append(f"• {it.title or it.problem or it.raw_content[:60]}")
                summary_text = "\n".join(items_summary)
                
                reply = f"Bugun guruhlar va ko'rsatmalardan {today_count} ta yangi foydali bilim o'rganildi (Umumiy baza: {total_count} ta).\n\nSo'nggi o'rganilganlar:\n{summary_text}"
            
            response_payload["reply_text"] = reply
            await self.memory.add_message(conv.id, "user", user_text)
            await self.memory.add_message(conv.id, "assistant", reply)
            return response_payload

        # ==========================================================
        # INTENT: RETRIEVE_ORIGINAL ("Tashlab ber")
        # ==========================================================
        if intent == "RETRIEVE_ORIGINAL":
            # Search recent raw messages or attachments
            search_query = intent_info.get("search_query") or user_text
            # Look at previous turn to know what was discussed
            prev_context = history[-1]["content"] if history else ""
            full_lookup_query = f"{user_text} {prev_context}"

            raw_msgs = await self.search_engine.search_raw_telegram_messages(full_lookup_query, limit=2)
            similar_attachments = await self.search_engine.search_similar_attachments(full_lookup_query, limit=1)

            if similar_attachments:
                att = similar_attachments[0]["attachment"]
                response_payload["media_file_id"] = att.telegram_file_id
                response_payload["reply_text"] = "Mana o'sha screenshot 👇"
                await self.memory.add_message(conv.id, "user", user_text)
                await self.memory.add_message(conv.id, "assistant", response_payload["reply_text"])
                return response_payload

            if raw_msgs:
                target = raw_msgs[0]
                link = make_telegram_message_link(
                    chat_id=target["chat_id"],
                    message_id=target["message_id"],
                    chat_username=target.get("group_username")
                )
                response_payload["forward_message_id"] = target["message_id"]
                response_payload["forward_chat_id"] = target["chat_id"]
                
                reply = f"Mana “{target['group_title']}” guruhidagi xabar:\n\n{target['text']}\n\n🔗 Havola: {link}"
                response_payload["reply_text"] = reply
                await self.memory.add_message(conv.id, "user", user_text)
                await self.memory.add_message(conv.id, "assistant", reply)
                return response_payload

        # ==========================================================
        # INTENT: SEARCH_KNOWLEDGE / GENERAL_CHAT / RAG
        # ==========================================================
        # 1. Retrieve relevant knowledge items via Hybrid Search
        search_results = await self.search_engine.search(user_text, limit=4)
        
        # 2. Build RAG Context
        context_snippets = []
        source_attributions = []

        for res in search_results:
            k: Knowledge = res["knowledge"]
            src: Optional[KnowledgeSource] = res.get("source")
            src_name = src.source_group_name or (src.author if src else "Baza")
            src_type = src.source_type.value if src else "SYSTEM"
            
            snippet = f"--- [Manba: {src_type} ({src_name})] ---\n"
            if k.problem:
                snippet += f"Muammo: {k.problem}\n"
            if k.possible_cause:
                snippet += f"Sabab: {k.possible_cause}\n"
            if k.solution:
                snippet += f"Yechim: {k.solution}\n"
            snippet += f"Mazmun: {k.raw_content}\n"
            context_snippets.append(snippet)
            source_attributions.append(f"{src_type} ({src_name})")

        rag_context_text = "\n\n".join(context_snippets) if context_snippets else "Bazada to'g'ridan-to'g'ri o'xshash ma'lumot topilmadi."

        # Format conversation history string
        history_formatted = ""
        for h in history[-6:]:
            history_formatted += f"{h['role'].capitalize()}: {h['content']}\n"

        prompt = f"""Quyida bazadagi tegishli bilimlar (RAG Context) keltirilgan:
{rag_context_text}

Oldingi suhbat tarixi:
{history_formatted}

Foydalanuvchining yangi xabari:
"{user_text}"

Eslatma:
- Foydalanuvchining oldingi shaxsiy ko'rsatmalari ("USER") bo'lsa, ularga qat'iy tayangan holda javob ber.
- Javobing tabiiy, samimiy, do'stona, o'zbek tilida (lotin) bo'lsin.
- Javobni sun'iy "AI Analysis" yoki "Confidence" kabi teglarsiz toza matn holida yoz.
"""
        reply = await self.client.generate_text(
            prompt=prompt,
            system_instruction=SYSTEM_ASSISTANT_PROMPT,
            temperature=0.3
        )

        response_payload["reply_text"] = reply
        await self.memory.add_message(conv.id, "user", user_text)
        await self.memory.add_message(conv.id, "assistant", reply, metadata_json={"sources": source_attributions})
        return response_payload
