"""
Group message knowledge extractor module.
Analyzes conversational threads from technical Telegram groups, filters trivial noise,
and extracts structured problem-cause-solution knowledge.
"""
from typing import List, Dict, Any, Optional
from app.ai.gemini_client import gemini_client
from app.ai.prompts import KNOWLEDGE_EXTRACTION_PROMPT
from app.utils.logger import logger


class KnowledgeExtractor:
    def __init__(self, client=gemini_client):
        self.client = client

    async def extract_from_group_messages(
        self,
        group_title: str,
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Analyzes a chronological batch of messages from a Telegram group.
        Returns extracted list of structured knowledge items.
        """
        if not messages:
            return []

        # Format message log for Gemini prompt
        formatted_log = []
        for msg in messages:
            sender = msg.get("sender_name") or msg.get("username") or "Foydalanuvchi"
            text = msg.get("text") or ""
            msg_id = msg.get("message_id")
            if text.strip():
                formatted_log.append(f"[MsgID:{msg_id}] {sender}: {text}")

        if not formatted_log:
            return []

        prompt = f"""Guruh nomi: "{group_title}"
Quyida ushbu guruhdagi yangi xabarlar oqimi berilgan:

{chr(10).join(formatted_log)}

Iltimos, ushbu xabarlar orasidan faqat foydali texnik tajriba, xatoliklar, sabablar va yechimlarni ajratib olib JSON ro'yxat ko'rinishida ber.
Oddiy gaplar, salomlashish yoki ahamiyatsiz suhbatlarni ignore qil.
"""

        raw_result = await self.client.generate_text(
            prompt=prompt,
            system_instruction=KNOWLEDGE_EXTRACTION_PROMPT,
            temperature=0.2,
            json_output=True
        )

        parsed = self.client.parse_json_response(raw_result)
        if isinstance(parsed, list):
            logger.info(f"Extracted {len(parsed)} knowledge items from group '{group_title}' ({len(messages)} messages)")
            return parsed
        elif isinstance(parsed, dict):
            return [parsed]
        
        return []


knowledge_extractor = KnowledgeExtractor()
