import json
import os
import urllib.request
from typing import Dict, Any
from pathlib import Path
from bol.utils.logging import get_logger

logger = get_logger(__name__)

# Default free-tier endpoint for OTA updates (e.g., GitHub Raw URL)
# The user can override this via environment variable if they move to Firebase or Cloudflare
DEFAULT_OTA_URL = os.environ.get(
    "AHA_OTA_WORKFLOWS_URL",
    "https://raw.githubusercontent.com/YourOrg/aha-workflows/main/workflows.json"
)

LOCAL_FALLBACK_PATH = Path(__file__).parent / "workflows.json"

def fetch_latest_workflows() -> Dict[str, Any]:
    """
    Attempts to fetch the latest social media workflows from the OTA endpoint.
    Falls back to the local `workflows.json` if offline or the request fails.
    """
    try:
        logger.info(f"Checking for OTA workflow updates at: {DEFAULT_OTA_URL}")
        req = urllib.request.Request(DEFAULT_OTA_URL, headers={'User-Agent': 'AHA-Client/1.0'})
        with urllib.request.urlopen(req, timeout=5.0) as response:
            if response.status == 200:
                data = response.read().decode('utf-8')
                workflows = json.loads(data)
                logger.info("Successfully fetched OTA workflow updates.")
                return workflows
    except Exception as e:
        logger.warning(f"Failed to fetch OTA workflows (might be offline or URL invalid): {str(e)}")
    
    logger.info(f"Falling back to local workflows definition at {LOCAL_FALLBACK_PATH}")
    if LOCAL_FALLBACK_PATH.exists():
        with open(LOCAL_FALLBACK_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        logger.error("Local fallback workflows.json not found!")
        return {"version": "1.0", "workflows": {}}
