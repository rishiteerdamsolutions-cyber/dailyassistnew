import json
from pathlib import Path
try:
    import google.generativeai as genai
except ImportError:
    genai = None

from bol.utils.logging import get_logger
from bol.config import get_config
from aha.media_folders import write_calendar_slot_media

logger = get_logger(__name__)

class ContentGenerator:
    """
    Generates 30 days of text content (captions) using Gemini 
    and writes them directly to the AHA Vault (Downloads/aha/...).
    """
    def __init__(self, api_key: str):
        if not genai:
            raise ImportError("google.generativeai is not installed.")
        
        self.api_key = api_key
        genai.configure(api_key=self.api_key)
        
        config = get_config()
        self.model = genai.GenerativeModel(
            model_name=config.gemini_model_name,
            system_instruction=(
                "You are an expert social media manager. The user will give you a topic or business description. "
                "You must generate exactly 30 distinct daily social media posts based on that topic. "
                "Output MUST be a pure JSON array of 30 strings. Do not use markdown code blocks. "
                'Example: ["Post 1 text", "Post 2 text", ..., "Post 30 text"]'
            )
        )

    def generate_30_days(self, topic: str, layer_key: str = "ai") -> list[str]:
        """
        Generates 30 posts and saves them to the file system.
        layer_key: 'core', 'hybrid', or 'ai'
        """
        logger.info(f"Prompting Gemini for 30 days of content on topic: {topic}")
        response = self.model.generate_content(f"Topic: {topic}")
        raw_text = response.text.strip()
        
        if raw_text.startswith("```json"):
            raw_text = raw_text.split("```json")[1]
        if raw_text.endswith("```"):
            raw_text = raw_text.rsplit("```", 1)[0]
        raw_text = raw_text.strip()

        try:
            posts = json.loads(raw_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from AI: {e}")
            raise ValueError(f"AI returned invalid JSON: {raw_text[:100]}...")

        if len(posts) < 30:
            logger.warning(f"AI only generated {len(posts)} posts instead of 30.")

        # Save to the file system
        # `write_calendar_slot_media` writes to ~/Downloads/aha/...
        downloads_base = Path.home() / "Downloads"
        
        saved_paths = []
        for i, post_text in enumerate(posts):
            day = i + 1
            if day > 30:
                break
                
            try:
                result = write_calendar_slot_media(
                    downloads_base=downloads_base,
                    flow_label="social",
                    workflow_key="social",
                    workflow_display="Social Media Routine",
                    layer_key=layer_key,
                    day=day,
                    slot_kind="text",
                    data=post_text.encode("utf-8"),
                )
                saved_paths.append(result["path"])
                logger.info(f"Saved day {day} text to {result['path']}")
            except Exception as e:
                logger.error(f"Failed to write day {day} file: {e}")

        return saved_paths
