import json
from datetime import date
from pathlib import Path

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from bol.utils.logging import get_logger
from bol.config import get_config
from aha.media_folders import write_calendar_slot_media
from aha.vault_slots import resolve_batch_days, write_slot_text

logger = get_logger(__name__)


class ContentGenerator:
    """
    BYOK caption generation — user's API key, writes into the Content Vault.
    """

    def __init__(self, api_key: str):
        if not genai:
            raise ImportError("google.generativeai is not installed.")

        self.api_key = api_key
        genai.configure(api_key=self.api_key)
        config = get_config()
        self._model_name = config.gemini_model_name

    def _model(self, *, num_posts: int) -> "genai.GenerativeModel":
        return genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=(
                "You are an expert social media writer. The user gives a topic. "
                f"Return exactly {num_posts} distinct short post captions as a JSON array of strings. "
                "No markdown fences. Example: [\"Caption one\", \"Caption two\"]"
            ),
        )

    @staticmethod
    def _parse_posts(raw_text: str, expected: int) -> list[str]:
        text = raw_text.strip()
        if text.startswith("```json"):
            text = text.split("```json", 1)[1]
        if text.startswith("```"):
            text = text.split("```", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()
        try:
            posts = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"AI returned invalid JSON: {text[:120]}...") from exc
        if not isinstance(posts, list):
            raise ValueError("AI response must be a JSON array of strings.")
        cleaned = [str(p).strip() for p in posts if str(p).strip()]
        if len(cleaned) < expected:
            logger.warning("AI returned %d posts; expected %d.", len(cleaned), expected)
        return cleaned[:expected]

    def generate_slot_batch(
        self,
        *,
        topic: str,
        num_days: int,
        slot: str,
        year: int | None = None,
        month: int | None = None,
        start_day: int | None = None,
    ) -> dict:
        """
        Generate *num_days* captions for *topic* and save to consecutive vault days.

        Example: first batch n=5 → days 1–5; next batch n=3 → days 6–8 (auto).
        """
        today = date.today()
        y = year if year is not None else today.year
        m = month if month is not None else today.month
        start, day_list = resolve_batch_days(slot, y, m, num_days, start_day=start_day)

        logger.info(
            "Generating %d captions for slot=%s %d-%02d days %s topic=%r",
            num_days,
            slot,
            y,
            m,
            day_list,
            topic,
        )
        model = self._model(num_posts=num_days)
        prompt = (
            f"Topic: {topic}\n"
            f"Write exactly {num_days} unique social post captions, one per calendar day. "
            f"Each caption should stand alone; vary angle and hook across days."
        )
        response = model.generate_content(prompt)
        posts = self._parse_posts(response.text, num_days)
        if len(posts) < num_days:
            raise ValueError(f"AI only returned {len(posts)} captions; need {num_days}.")

        saved: list[dict] = []
        for day, caption in zip(day_list, posts):
            path = write_slot_text(slot, y, m, day, caption)
            saved.append({"day": day, "path": str(path)})
            logger.info("Saved vault text day %d → %s", day, path)

        next_start = day_list[-1] + 1
        return {
            "slot": slot,
            "year": y,
            "month": m,
            "start_day": start,
            "days": day_list,
            "saved": saved,
            "next_start_day": next_start if next_start <= 31 else None,
            "topic": topic,
        }

    def generate_30_days(self, topic: str, layer_key: str = "ai") -> list[str]:
        """Legacy writer — Downloads/aha plan folders (scheduler compatibility)."""
        model = self._model(num_posts=30)
        response = model.generate_content(f"Topic: {topic}")
        posts = self._parse_posts(response.text, 30)

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
            except Exception as exc:
                logger.error("Failed to write day %d file: %s", day, exc)

        return saved_paths
