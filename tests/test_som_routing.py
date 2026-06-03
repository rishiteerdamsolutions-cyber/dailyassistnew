"""
Tests for Set-of-Mark (SoM) visual grouping and precision coordinate clicks.
"""

from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from bol.config import BOLConfig
from bol.modules.m3_visual.ocr import OCREngine
from bol.modules.m8_orchestrator.agent import AutonomousCompanion
from bol.schemas.visual import BoundingBox, OCRWord, OCRResult
from bol.schemas.kinematic import Point2D


def test_group_words_into_blocks() -> None:
    ocr_engine = OCREngine()
    
    # Create word-level words on the same line, close horizontally
    # "Add" at x=100, y=200, w=30, h=20
    # "to" at x=135, y=202, w=20, h=18
    # "cart" at x=160, y=201, w=35, h=20
    words = [
        OCRWord(text="Add", bounding_box=BoundingBox(x=100, y=200, width=30, height=20), confidence=90),
        OCRWord(text="to", bounding_box=BoundingBox(x=135, y=202, width=20, height=18), confidence=85),
        OCRWord(text="cart", bounding_box=BoundingBox(x=160, y=201, width=35, height=20), confidence=95),
        
        # Word on a different line
        OCRWord(text="Flight", bounding_box=BoundingBox(x=100, y=300, width=50, height=20), confidence=80)
    ]
    
    grouped = ocr_engine.group_words_into_blocks(words)
    
    # We expect 2 blocks: "Add to cart" and "Flight"
    assert len(grouped) == 2
    
    # Assert "Add to cart" properties
    assert grouped[0].text == "Add to cart"
    assert grouped[0].bounding_box.x == 100
    assert grouped[0].bounding_box.y == 200 # min y
    assert grouped[0].bounding_box.width == 95 # x_max (160+35) - x_min (100)
    assert grouped[0].bounding_box.height == 21 # max bottom (200+20) - min y (200) -> 221 - 200 = 21
    
    # Assert "Flight" properties
    assert grouped[1].text == "Flight"
    assert grouped[1].bounding_box.x == 100
    assert grouped[1].bounding_box.y == 300


@patch('google.generativeai.configure')
def test_direct_coordinate_click_routing(mock_configure: MagicMock) -> None:
    config = BOLConfig()
    config.gemini_api_key = "mock_key"
    config.openai_api_key = "mock_openai_key"
    config.browser_window_enabled = True
    config.browser_window_x = 500
    config.browser_window_y = 100
    
    companion = AutonomousCompanion(config)
    
    # Prepare some mock candidate blocks
    box_target = BoundingBox(x=100, y=200, width=50, height=20)
    candidate = OCRWord(text="Click Me", bounding_box=box_target, confidence=90)
    
    # Mock bridge position and movements
    companion.bridge.get_cursor_position = MagicMock(return_value=Point2D(x=0, y=0))
    companion.bridge.execute_movement = MagicMock()
    companion.bridge.execute_click = MagicMock()
    
    # Mock _capture_and_encode to return dummy and set latest_bgr
    dummy_bgr = np.zeros((400, 400, 3), dtype=np.uint8)
    from PIL import Image
    dummy_pil = Image.fromarray(dummy_bgr)
    
    def mock_capture():
        companion.latest_bgr = dummy_bgr
        return dummy_pil
        
    companion._capture_and_encode = mock_capture
    
    # Mock response indicating precision box click target
    # We call step() with a mock OpenAI response pointing to box:0
    with patch('openai.OpenAI') as mock_openai_cls:
        mock_openai_inst = MagicMock()
        mock_openai_cls.return_value = mock_openai_inst
        
        # Setup mock OCR to return our candidate block as part of group_words_into_blocks
        mock_ocr_res = MagicMock()
        mock_ocr_res.words = []
        mock_ocr_res.full_text = "Click Me"
        companion.cortex._ocr.extract_text = MagicMock(return_value=mock_ocr_res)
        
        # Ensure our candidate is returned as the block
        companion.cortex._ocr.group_words_into_blocks = MagicMock(return_value=[candidate])
        
        mock_choice = MagicMock()
        # VLM decides to click "box:0" (the Precision box click target)
        mock_choice.message.content = '{"action": "click", "target": "box:0", "current_plan_step": 0, "next_plan_step": 1}'
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_openai_inst.chat.completions.create.return_value = mock_response
        
        # Enable vision routing to trigger OpenAI
        companion.current_plan = [{"id": 0, "description": "checkout", "complexity": "hard"}]
        companion.current_plan_step = 0
        
        res = companion.step()
        
        # Ensure it clicked at the center of box 0 with browser coordinates offsets
        # center of box = (100 + 25, 200 + 10) = (125, 210)
        # offset = (500, 100) -> final click center should be within target bounds
        # expected X range: [100 + 500, 100 + 50 + 500] = [600, 650]
        # expected Y range: [200 + 100, 200 + 20 + 100] = [300, 320]
        
        assert companion.bridge.execute_click.called
        click_args = companion.bridge.execute_click.call_args[0][0]
        assert 600 <= click_args.target_x <= 650
        assert 300 <= click_args.target_y <= 320
        
        assert "Successfully clicked" in res["messages"][-1]
