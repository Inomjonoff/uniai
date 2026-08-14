"""
Gemini AI Client wrapper for Chat, Vision, and Text Embeddings.
Powered by modern Google GenAI SDK (google-genai) with automated fallback.
"""
import io
import json
import re
from typing import List, Dict, Any, Optional, Union
from PIL import Image

try:
    from google import genai as modern_genai
    from google.genai import types as genai_types
    MODERN_GENAI_AVAILABLE = True
except ImportError:
    modern_genai = None
    genai_types = None

from app.config import settings
from app.utils.logger import logger

DEFAULT_CANDIDATE_MODELS = [
    "gemini-3-flash-preview",
    "gemini-flash-latest",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash"
]

DEFAULT_EMBEDDING_MODELS = [
    "gemini-embedding-001",
    "gemini-embedding-2",
    "text-embedding-004"
]


class GeminiClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = settings.gemini_model or "gemini-3-flash-preview"
        self.embedding_model = settings.embedding_model or "gemini-embedding-001"
        self.modern_client = None
        self._configured = False

        if self.api_key and MODERN_GENAI_AVAILABLE:
            try:
                self.modern_client = modern_genai.Client(api_key=self.api_key)
                self._configured = True
                logger.info(f"Initialized modern google-genai client with default model: {self.model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize modern genai client: {e}")
        else:
            logger.warning("Gemini API key is not set or SDK missing. Operating in fallback mode.")

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.4,
        json_output: bool = False
    ) -> str:
        """Generates text using modern google.genai with automated model fallback."""
        if not self._configured or not self.modern_client:
            logger.warning("Gemini not configured, returning local fallback response.")
            return "Gemini API sozlanmagan. Iltimos .env faylida GEMINI_API_KEY ni ko'rsating."

        models_to_try = [self.model_name] + [m for m in DEFAULT_CANDIDATE_MODELS if m != self.model_name]

        config_kwargs = {"temperature": temperature}
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if json_output:
            config_kwargs["response_mime_type"] = "application/json"

        config = genai_types.GenerateContentConfig(**config_kwargs)

        for target_model in models_to_try:
            try:
                response = await self.modern_client.aio.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=config
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                logger.warning(f"Model {target_model} failed: {e}. Trying next candidate...")
                continue

        return "Gemini modelidan javob olib bo'lmadi. Iltimos qaytadan urinib ko'ring."

    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str,
        system_instruction: Optional[str] = None
    ) -> str:
        """Analyzes an image using Gemini Vision with automated model fallback."""
        if not self._configured or not self.modern_client:
            return "Gemini Vision sozlanmagan. Iltimos GEMINI_API_KEY ni tekshiring."

        image = Image.open(io.BytesIO(image_bytes))
        models_to_try = [self.model_name] + [m for m in DEFAULT_CANDIDATE_MODELS if m != self.model_name]

        config = genai_types.GenerateContentConfig(
            system_instruction=system_instruction
        ) if system_instruction else None

        for target_model in models_to_try:
            try:
                response = await self.modern_client.aio.models.generate_content(
                    model=target_model,
                    contents=[image, prompt],
                    config=config
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                logger.warning(f"Vision model {target_model} failed: {e}. Trying next candidate...")
                continue

        return "Screenshotni tahlil qilishda xatolik yuz berdi."

    async def generate_embedding(self, text: str) -> List[float]:
        """Generates text embedding with automated model fallback."""
        if not text or not text.strip():
            return [0.0] * 3072

        if not self._configured or not self.modern_client:
            import hashlib
            h = hashlib.sha256(text.encode("utf-8")).digest()
            return [(b / 128.0 - 1.0) for b in (h * 96)[:3072]]

        models_to_try = [self.embedding_model] + [m for m in DEFAULT_EMBEDDING_MODELS if m != self.embedding_model]

        for target_model in models_to_try:
            try:
                result = await self.modern_client.aio.models.embed_content(
                    model=target_model,
                    contents=text
                )
                if hasattr(result, "embeddings") and result.embeddings:
                    return list(result.embeddings[0].values)
                if hasattr(result, "embedding") and hasattr(result.embedding, "values"):
                    return list(result.embedding.values)
            except Exception as e:
                logger.warning(f"Embedding model {target_model} failed: {e}. Trying next candidate...")
                continue

        import hashlib
        h = hashlib.sha256(text.encode("utf-8")).digest()
        return [(b / 128.0 - 1.0) for b in (h * 96)[:3072]]

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
