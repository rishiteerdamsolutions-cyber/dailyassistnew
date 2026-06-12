"""
Tests for OpenAI routing and history mapper in AutonomousCompanion.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from bol.config import BOLConfig
from bol.modules.m8_orchestrator.agent import AutonomousCompanion

class MockContent:
    """Mock protobuf Content object for Gemini."""
    def __init__(self, role: str, text: str):
        self.role = role
        self.parts = [MockPart(text)]

class MockPart:
    """Mock Part object."""
    def __init__(self, text: str):
        self.text = text

def test_get_openai_messages_conversion() -> None:
    config = BOLConfig()
    config.gemini_api_key = "mock_gemini_key"
    config.openai_api_key = "mock_openai_key"
    config.openai_model_name = "gpt-4o"

    with patch('google.generativeai.configure') as mock_configure:
        companion = AutonomousCompanion(config)
        
        # Populate self.chat_history with mixed Content objects and dictionaries
        companion.chat_history = [
            MockContent(role="user", text="hello"),
            MockContent(role="model", text="hi there"),
            {"role": "user", "parts": ["how are you?"]},
            {"role": "model", "parts": [{"text": "good!"}]}
        ]

        # Test base history translation
        messages = companion._get_openai_messages(prompt="what next?")
        
        # The expected output should have 1 system message, 4 history messages, and 1 current user prompt
        assert len(messages) == 6
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "hello"
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "hi there"
        assert messages[3]["role"] == "user"
        assert messages[3]["content"] == "how are you?"
        assert messages[4]["role"] == "assistant"
        assert messages[4]["content"] == "good!"
        
        # Current user turn
        assert messages[5]["role"] == "user"
        assert isinstance(messages[5]["content"], list)
        assert messages[5]["content"][0]["type"] == "text"
        assert messages[5]["content"][0]["text"] == "what next?"

def test_get_openai_messages_with_vision() -> None:
    config = BOLConfig()
    config.gemini_api_key = "mock_gemini_key"
    config.openai_api_key = "mock_openai_key"

    with patch('google.generativeai.configure') as mock_configure:
        companion = AutonomousCompanion(config)
        companion.needs_vision = True

        messages = companion._get_openai_messages(prompt="check this out", current_image_base64="data:image/jpeg;base64,mockbase64")
        
        assert len(messages) == 2 # system + user current
        assert messages[1]["role"] == "user"
        content = messages[1]["content"]
        assert len(content) == 2
        assert content[0]["type"] == "text"
        assert content[0]["text"] == "check this out"
        assert content[1]["type"] == "image_url"
        assert content[1]["image_url"]["url"] == "data:image/jpeg;base64,mockbase64"

def test_openai_routing_hard_complexity() -> None:
    config = BOLConfig()
    config.gemini_api_key = "mock_gemini_key"
    config.openai_api_key = "mock_openai_key"
    config.openai_model_name = "gpt-4o"

    with patch('google.generativeai.configure') as mock_configure, \
         patch('bol.modules.m8_orchestrator.agent.AutonomousCompanion._capture_and_encode') as mock_capture, \
         patch('openai.OpenAI') as mock_openai_cls:
        
        companion = AutonomousCompanion(config)
        
        # Setup plan with a hard step
        companion.current_plan = [{"id": 0, "description": "checkout", "complexity": "hard"}]
        companion.current_plan_step = 0

        # Mock dependencies
        mock_capture.return_value = MagicMock()
        mock_openai_inst = MagicMock()
        mock_openai_cls.return_value = mock_openai_inst
        
        # Setup dummy BGR array and mock OCR to avoid external dependencies/exceptions
        import numpy as np
        companion.latest_bgr = np.zeros((100, 100, 3), dtype=np.uint8)
        companion.cortex._ocr.extract_text = MagicMock()
        mock_ocr_res = MagicMock()
        mock_ocr_res.full_text = "test screen text"
        mock_ocr_res.words = []
        companion.cortex._ocr.extract_text.return_value = mock_ocr_res

        # Mock choice response
        mock_choice = MagicMock()
        mock_choice.message.content = '{"action": "done", "message": "Success", "next_plan_step": 1}'
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_openai_inst.chat.completions.create.return_value = mock_response

        # Execute step
        res = companion.step()
        
        # Should initialize OpenAI client with correct key and model
        mock_openai_cls.assert_called_once_with(api_key="mock_openai_key")
        mock_openai_inst.chat.completions.create.assert_called_once()
        kwargs = mock_openai_inst.chat.completions.create.call_args[1]
        assert kwargs["model"] == "gpt-4o"
        assert kwargs["response_format"] == {"type": "json_object"}
        
        # Check output and history update
        assert res["is_done"] is True
        assert len(companion.chat_history) == 2
        assert companion.chat_history[0]["role"] == "user"
        assert companion.chat_history[1]["role"] == "model"
        assert "Success" in companion.chat_history[1]["parts"][0]
