import time
import threading
from pathlib import Path
from datetime import datetime

from bol.utils.logging import get_logger
from bol.config import get_config
from bol.modules.m8_orchestrator.workflow_runner import WorkflowRunner
from aha.media_folders import resolve_layer_day_paths, compute_calendar_day_index

logger = get_logger(__name__)

class RoutineScheduler:
    """
    Background daemon that wakes up at a specific time daily,
    determines the current campaign day, grabs the assets for that day,
    and runs the social media workflows.
    """
    def __init__(self, target_time: str = "09:00"):
        self.target_time = target_time
        self.is_running = False
        self._thread = None
        self.config = get_config()
        self.runner = WorkflowRunner(self.config)
        self.platforms = ["linkedin_post", "facebook_post", "instagram_post", "x_post", "whatsapp_status"]

    def start(self):
        if self.is_running:
            logger.warning("Scheduler is already running.")
            return
        
        self.is_running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info(f"Routine Scheduler started. Will execute daily at {self.target_time}.")

    def stop(self):
        self.is_running = False
        logger.info("Routine Scheduler stopped.")

    def _loop(self):
        # Prevent double execution on the same day
        last_run_date = None
        
        while self.is_running:
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            current_date = now.strftime("%Y-%m-%d")
            
            if current_time == self.target_time and current_date != last_run_date:
                logger.info(f"Time matches {self.target_time}. Initiating daily routine.")
                self.execute_daily_routine()
                last_run_date = current_date
                
            time.sleep(30) # Check every 30 seconds

    def execute_daily_routine(self):
        """
        Manually triggerable function to run today's routine immediately.
        """
        logger.info("Executing Social Media Routine...")
        downloads_base = Path.home() / "Downloads"
        
        # In a real app, this value comes from a local sqlite DB or config file.
        # For now we use the environment variable fallback system from `aha`.
        runtime_vars = {} 
        day_index = compute_calendar_day_index(runtime_vars)
        
        logger.info(f"Computed Campaign Day: {day_index}")
        
        # Using "ai" layer for the generated texts, but checking "core" for images if needed.
        # According to the user's instructions, they will drop the images into the respective AI Pro folders.
        paths = resolve_layer_day_paths(downloads_base, layer_key="ai", day=day_index, runtime_vars=runtime_vars)
        
        txt_path = paths.get("text")
        img_path = paths.get("image")
        vid_path = paths.get("video")
        
        caption = ""
        if txt_path and txt_path.exists():
            try:
                caption = txt_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to read caption file {txt_path}: {e}")
                
        # Prefer video over image if both exist (rare)
        media_path = str(vid_path.resolve()) if vid_path else (str(img_path.resolve()) if img_path else "")

        context = {
            "$FILE_PATH": media_path,
            "$CAPTION": caption
        }
        
        for platform in self.platforms:
            logger.info(f"--- Starting {platform} for Day {day_index} ---")
            success = self.runner.run_workflow(platform, context)
            if not success:
                logger.error(f"Failed to complete {platform}. Moving to next.")
            time.sleep(5) # Pause between platforms
            
        logger.info(f"Daily routine for Day {day_index} completed.")
        
        # After successful completion, we would theoretically increment CURRENT_CAMPAIGN_DAY in the DB.
        # For now, it relies on the user's `CUSEAR_CALENDAR_CYCLE` mapping.
