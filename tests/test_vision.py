"""
Unit tests for Vision and Document extractors.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.ai.vision import VisionAnalyzer
from app.ai.file_processor import FileProcessor
from app.ai.gemini_client import GeminiClient


@pytest.mark.asyncio
async def test_vision_analyzer_parses_json_metadata():
    mock_client = MagicMock(spec=GeminiClient)
    mock_client.analyze_image = AsyncMock(return_value="""Ko'rdim. Bu yerda 500 Internal Server Error chiqyapti. Backend API servisni tekshirish kerak.
```json
{
  "ocr_text": "HTTP 500 Internal Server Error",
  "detected_errors": ["500 Internal Server Error"],
  "system_name": "Ijro.gov.uz API"
}
```""")
    mock_client.generate_embedding = AsyncMock(return_value=[0.2] * 768)
    mock_client.parse_json_response = GeminiClient.parse_json_response

    analyzer = VisionAnalyzer(client=mock_client)
    res = await analyzer.analyze_screenshot(b"fake_image_bytes", user_caption="Bu nima?")

    assert "500 Internal Server Error" in res["natural_response"]
    assert res["ocr_text"] == "HTTP 500 Internal Server Error"
    assert res["system_name"] == "Ijro.gov.uz API"
    assert len(res["embedding"]) == 768


def test_file_processor_text_chunking():
    processor = FileProcessor()

    sample_text = ("UNICON-SOFT texnik yo'riqnomasi.\n" * 50)  # ~1600 chars
    chunks = processor.chunk_text(sample_text, chunk_size=500, overlap=50)

    assert len(chunks) > 1
    assert "UNICON-SOFT" in chunks[0]
