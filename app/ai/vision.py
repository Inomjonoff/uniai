"""
Vision and Screenshot Analysis module.
Extracts OCR text, identifies errors, detects system context, generates embeddings,
and stores metadata in the Attachment table.
"""
from typing import Dict, Any, Optional, List
import json
from app.ai.gemini_client import gemini_client
from app.ai.prompts import VISION_ANALYSIS_PROMPT, SYSTEM_ASSISTANT_PROMPT
from app.utils.logger import logger


class VisionAnalyzer:
    def __init__(self, client=gemini_client):
        self.client = client

    async def analyze_screenshot(
        self,
        image_bytes: bytes,
        user_caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyzes a technical screenshot using Gemini Vision.
        Returns natural explanation, OCR text summary, detected errors, and embedding.
        """
        prompt = f"""Foydalanuvchi quyidagi savol/izohni yozdi: "{user_caption or 'Bu nima xato? Tahlil qilib ber.'}"

Iltimos, screenshotni ko'rib:
1. Qanday xatolik (status code, exception yoki stack trace) borligini aniqla.
2. Qaysi tizim yoki muhit (UI, console, swagger, postman va h.k.) ekanligini ayt.
3. Qisqa va tushunarli tarzda (tabiiy o'zbek tilida) nima bo'lganini va qanday tuzatish mumkinligini tushuntir.
4. Javobing oxirida yashirin JSON blokida OCR matni va xatoliklar ro'yxatini quyidagicha keltir:
```json
{{
  "ocr_text": "rasmdagi asosiy xato matni",
  "detected_errors": ["500 Internal Server Error", "DatabaseConnectionTimeout"],
  "system_name": "Ijro.gov.uz / Nginx / Backend"
}}
```
"""
        raw_response = await self.client.analyze_image(
            image_bytes=image_bytes,
            prompt=prompt,
            system_instruction=SYSTEM_ASSISTANT_PROMPT
        )

        # Extract JSON metadata if present
        metadata = {
            "ocr_text": "",
            "detected_errors": [],
            "system_name": "General"
        }
        natural_response = raw_response

        if "```json" in raw_response:
            parts = raw_response.split("```json")
            natural_response = parts[0].strip()
            json_part = parts[1].split("```")[0].strip()
            parsed = self.client.parse_json_response(json_part)
            if isinstance(parsed, dict):
                metadata.update(parsed)

        # Generate embedding for the OCR / description to enable future screenshot retrieval
        searchable_text = f"{metadata.get('ocr_text', '')} {' '.join(metadata.get('detected_errors', []))} {natural_response}"
        embedding = await self.client.generate_embedding(searchable_text)

        return {
            "natural_response": natural_response,
            "ocr_text": metadata.get("ocr_text", ""),
            "detected_errors": metadata.get("detected_errors", []),
            "system_name": metadata.get("system_name", "General"),
            "embedding": embedding
        }


vision_analyzer = VisionAnalyzer()
