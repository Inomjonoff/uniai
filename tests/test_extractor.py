"""
Unit tests for Group Message Knowledge Extractor.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.ai.extractor import KnowledgeExtractor
from app.ai.gemini_client import GeminiClient


@pytest.mark.asyncio
async def test_extractor_processes_technical_messages():
    mock_client = MagicMock(spec=GeminiClient)
    mock_client.generate_text = AsyncMock(return_value="""[
      {
        "title": "502 Bad Gateway Nginx Restart",
        "problem": "Serverda 502 Bad Gateway chiqishi",
        "possible_cause": "Backend servis o'chib qolgan",
        "solution": "Nginx va backend servisni tekshirish va restart qilish",
        "raw_content": "502 bo'lganda backend o'chib qolgan edi, restart bilan ishladi",
        "category": "backend",
        "tags": ["502", "nginx", "restart"],
        "confidence": 0.9,
        "source_message_ids": [101, 102, 103],
        "participants": ["Ali", "Vali", "Hasan"]
      }
    ]""")
    mock_client.parse_json_response = GeminiClient.parse_json_response

    extractor = KnowledgeExtractor(client=mock_client)

    messages = [
        {"message_id": 100, "sender_name": "Ali", "text": "Salom hammaga"},
        {"message_id": 101, "sender_name": "Ali", "text": "Serverda 502 chiqyapti"},
        {"message_id": 102, "sender_name": "Vali", "text": "Nginxni tekshirdingmi?"},
        {"message_id": 103, "sender_name": "Hasan", "text": "Backend service o'chib qolgan ekan, restart qildim ishladi"},
        {"message_id": 104, "sender_name": "Ali", "text": "Rahmat kattakon!"}
    ]

    extracted = await extractor.extract_from_group_messages(
        group_title="Ijro.gov.uz texnik",
        messages=messages
    )

    assert len(extracted) == 1
    item = extracted[0]
    assert item["title"] == "502 Bad Gateway Nginx Restart"
    assert "Backend servis o'chib qolgan" in item["possible_cause"]
    assert 101 in item["source_message_ids"]
    assert "Hasan" in item["participants"]


@pytest.mark.asyncio
async def test_extractor_handles_empty_or_trivial_messages():
    mock_client = MagicMock(spec=GeminiClient)
    mock_client.generate_text = AsyncMock(return_value="[]")
    mock_client.parse_json_response = GeminiClient.parse_json_response

    extractor = KnowledgeExtractor(client=mock_client)

    messages = [
        {"message_id": 201, "sender_name": "Botir", "text": "Salom"},
        {"message_id": 202, "sender_name": "Davron", "text": "Salom qalesan"},
        {"message_id": 203, "sender_name": "Botir", "text": "Yaxshi rahmat"}
    ]

    extracted = await extractor.extract_from_group_messages(
        group_title="General Chat",
        messages=messages
    )

    assert extracted == []
