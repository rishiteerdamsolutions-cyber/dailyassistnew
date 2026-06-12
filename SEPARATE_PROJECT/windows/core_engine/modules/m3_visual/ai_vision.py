from __future__ import annotations

import io
from typing import Optional

import numpy as np
from PIL import Image

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from bol.config import BOLConfig
from bol.utils.logging import get_logger

logger = get_logger(__name__)


class AIVisionEngine:
    """
    Integrates with Gemini Vision API to resolve user intents
    into exact on-screen text targets.
    """

    def __init__(self, config: BOLConfig) -> None:
        """
        Initialize the AI Vision Engine with Gemini credentials.
        """
        self.config = config
        self._enabled = False

        if config.vision_provider == "gemini":
            if not config.gemini_api_key:
                logger.warning("Gemini Vision requested but no API key found in BOL_GEMINI_API_KEY.")
            elif genai is None:
                logger.warning("google-generativeai package is not installed. AI Vision disabled.")
            else:
                genai.configure(api_key=config.gemini_api_key)
                self.model = genai.GenerativeModel(config.gemini_model_name)
                self._enabled = True
                logger.info("Initialized Gemini AI Vision Engine (model: %s)", config.gemini_model_name)
        else:
            logger.info("AI Vision Engine disabled (provider set to '%s')", config.vision_provider)

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def get_target_text_for_intent(self, screen_image: np.ndarray, intent: str) -> Optional[str]:
        """
        Given a screenshot and a user intent, ask the AI to find the exact text
        of the button or link to click.

        Parameters
        ----------
        screen_image : np.ndarray
            The current screen capture (OpenCV BGR format).
        intent : str
            The high-level user intent (e.g., "book air india flight").

        Returns
        -------
        str | None
            The exact text of the target to click, or None if not found or disabled.
        """
        if not self._enabled:
            logger.error("Cannot resolve intent: AIVisionEngine is not enabled.")
            return None

        logger.info("Asking Gemini AI to find target for intent: '%s'", intent)

        # Convert OpenCV BGR to RGB, then to PIL Image
        rgb_image = screen_image[..., ::-1]
        pil_image = Image.fromarray(rgb_image)

        prompt = (
            f"You are a GUI automation assistant. Look at the provided screenshot of a user interface.\n"
            f"The user wants to accomplish the following intent: '{intent}'\n\n"
            f"Your task is to identify the button, link, or tab that the user should click next to accomplish this intent.\n"
            f"Respond with ONLY the exact, verbatim text written on that element. Do not include any quotes, markdown, or extra words. "
            f"If there is absolutely no relevant element on screen, respond with exactly 'NOT_FOUND'."
        )

        try:
            response = self.model.generate_content([prompt, pil_image])
            result_text = response.text.strip()
            
            if result_text == "NOT_FOUND":
                logger.info("Gemini AI could not find a matching target on screen.")
                return None
                
            # Clean up the output in case the model added quotes despite instructions
            result_text = result_text.strip("\"'")
            logger.info("Gemini AI resolved intent to target text: '%s'", result_text)
            return result_text
            
        except Exception as e:
            logger.error("Error communicating with Gemini API: %s", str(e))
            return None
