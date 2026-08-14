"""
Gemini AI Client wrapper for Chat, Vision, and Text Embeddings.
Supports modern google-genai SDK with fallback to google.generativeai and deterministic offline mock.
"""
import io
import json
import re
from typing import List, Dict, Any, Optional, Union
from PIL import Image

# Try modern google.genai first
MODERN_GENAI_AVAILABLE = False
LEGACY_GENAI_AVAILABLE = False

try:
    from google import genai as modern_genai
    from google.genai import types as genai_types
    MODERN_GENAI_AVAILABLE = True
except ImportError:
    modern_genai = None
    genai_types = None

try:
    import google.generativeai as legacy_genai
    LEGACY_GENAI_AVAILABLE = True
except ImportError:
    legacy_genai = None

from app.config import settings
from app.utils.logger import logger


class GeminiClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = settings.gemini_model
        self.embedding_model = settings.embedding_model
        self.modern_client = None
        self._configured = False

        if self.api_key:
            if MODERN_GENAI_AVAILABLE:
                try:
                    self.modern_client = modern_genai.Client(api_key=self.api_key)
                    self._configured = True
                    logger.info(f"Initialized modern google-genai client with model: {self.model_name}")
                except Exception as e:
                    logger.warning(f"Failed to initialize modern genai client: {e}")

            if not self._configured and LEGACY_GENAI_AVAILABLE:
                try:
                    legacy_genai.configure(api_key=self.api_key)
                    self._configured = True
                    logger.info(f"Initialized legacy google-generativeai client with model: {self.model_name}")
                except Exception as e:
                    logger.error(f"Failed to configure legacy genai: {e}")
        else:
            logger.warning("Gemini API key is not set. Operating in offline/fallback mode.")

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.4,
        json_output: bool = False
    ) -> str:
        """Generates text using the configured Gemini model."""
        if not self._configured:
            logger.warning("Gemini not configured, returning local fallback response.")
            return "Gemini API sozlanmagan. Iltimos .env faylida GEMINI_API_KEY ni ko'rsating."

        # 1. Modern google.genai
        if self.modern_client:
            try:
                config_kwargs = {"temperature": temperature}
                if system_instruction:
                    config_kwargs["system_instruction"] = system_instruction
                if json_output:
                    config_kwargs["response_mime_type"] = "application/json"

                config = genai_types.GenerateContentConfig(**config_kwargs)
                response = await self.modern_client.aio.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config
                )
                return response.text.strip() if response and response.text else ""
            except Exception as e:
                logger.error(f"Error in modern genai generate_content: {e}", exc_info=True)

        # 2. Legacy google.generativeai fallback
        if LEGACY_GENAI_AVAILABLE:
            try:
                generation_config = {"temperature": temperature}
                if json_output:
                    generation_config["response_mime_type"] = "application/json"

                model = legacy_genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=system_instruction,
                    generation_config=generation_config
                )
                response = await model.generate_content_async(prompt)
                return response.text.strip() if response and response.text else ""
            except Exception as e:
                logger.error(f"Error in legacy genai generate_content: {e}", exc_info=True)
                return f"Xatolik yuz berdi: {str(e)}"

        return "Gemini API mavjud emas."

    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str,
        system_instruction: Optional[str] = None
    ) -> str:
        """Analyzes an image using Gemini Vision."""
        if not self._configured:
            return "Gemini Vision sozlanmagan. Iltimos GEMINI_API_KEY ni tekshiring."

        image = Image.open(io.BytesIO(image_bytes))

        # 1. Modern google.genai
        if self.modern_client:
            try:
                config = genai_types.GenerateContentConfig(
                    system_instruction=system_instruction
                ) if system_instruction else None

                response = await self.modern_client.aio.models.generate_content(
                    model=self.model_name,
                    contents=[image, prompt],
                    config=config
                )
                return response.text.strip() if response and response.text else ""
            except Exception as e:
                logger.error(f"Error in modern genai analyze_image: {e}", exc_info=True)

        # 2. Legacy fallback
        if LEGACY_GENAI_AVAILABLE:
            try:
                model = legacy_genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=system_instruction
                )
                response = await model.generate_content_async([image, prompt])
                return response.text.strip() if response and response.text else ""
            except Exception as e:
                logger.error(f"Error in legacy vision analysis: {e}", exc_info=True)
                return f"Screenshotni tahlil qilishda xatolik bo'ldi: {str(e)}"

        return "Gemini Vision mavjud emas."

    async def generate_embedding(self, text: str) -> List[float]:
        """Generates 768-dimensional text embedding."""
        if not text or not text.strip():
            return [0.0] * 768

        if not self._configured:
            # Deterministic mock embedding for offline tests
            import hashlib
            h = hashlib.sha256(text.encode("utf-8")).digest()
            return [(b / 128.0 - 1.0) for b in (h * 24)[:768]]

        # 1. Modern google.genai
        if self.modern_client:
            try:
                result = await self.modern_client.aio.models.embed_content(
                    model=self.embedding_model,
                    contents=text
                )
                if hasattr(result, "embeddings") and result.embeddings:
                    return list(result.embeddings[0].values)
                if hasattr(result, "embedding") and hasattr(result.embedding, "values"):
                    return list(result.embedding.values)
            except Exception as e:
                logger.error(f"Error in modern genai embed_content: {e}")

        # 2. Legacy fallback
        if LEGACY_GENAI_AVAILABLE:
            try:
                result = legacy_genai.embed_content(
                    model=f"models/{self.embedding_model}",
                    content=text,
                    task_type="retrieval_document"
                )
                embedding = result.get("embedding", [])
                if isinstance(embedding, dict) and "values" in embedding:
                    return embedding["values"]
                return list(embedding)
            except Exception as e:
                logger.error(f"Error in legacy embed_content: {e}")

        # Fallback vector
        import hashlib
        h = hashlib.sha256(text.encode("utf-8")).digest()
        return [(b / 128.0 - 1.0) for b in (h * 24)[:768]]

    @staticmethod
    def parse_json_response(raw_text: str) -> Optional[Union[Dict, List]]:
        """Cleans and parses JSON from model responses containing markdown backticks."""
        if not raw_text:
            return None
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}. Raw: {raw_text[:200]}")
            return None


gemini_client = GeminiClient()
