"""Social executor step confirmation logic."""

from unittest.mock import MagicMock, patch

import numpy as np

from bol.modules.m9_social.executor import SocialFlowExecutor
from bol.modules.m9_social.flows import Step, ActionType


def _blank_screen():
    return np.zeros((100, 100, 3), dtype=np.uint8)


def test_verify_step_confirmation_skips_when_no_confirm_fields():
    ex = SocialFlowExecutor()
    step = Step(number=1, description="noop", action=ActionType.WAIT, wait_seconds=0)
    assert ex._verify_step_confirmation(step, max_wait=0.5) is True


def test_verify_step_confirmation_detects_template():
    ex = SocialFlowExecutor()
    step = Step(
        number=2,
        description="confirm",
        action=ActionType.CLICK,
        confirm_template="instagram_share_button",
    )
    match = MagicMock()
    match.confidence = 0.9

    with patch.object(ex, "_get_cropped_screen_and_offset", return_value=(_blank_screen(), (0, 0))):
        with patch.object(ex._lib, "find", return_value=match):
            assert ex._verify_step_confirmation(step, max_wait=1.0) is True


def test_verify_step_confirmation_detects_text():
    ex = SocialFlowExecutor()
    step = Step(
        number=3,
        description="confirm text",
        action=ActionType.CLICK,
        confirm_text="Posted",
    )

    with patch.object(ex, "_get_cropped_screen_and_offset", return_value=(_blank_screen(), (0, 0))):
        with patch("pytesseract.image_to_string", return_value="Successfully Posted today"):
            assert ex._verify_step_confirmation(step, max_wait=1.0) is True
