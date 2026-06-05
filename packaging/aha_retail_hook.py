"""PyInstaller runtime hook — mark retail builds (no dev license bypass)."""
import os

os.environ["AHA_RETAIL_BUILD"] = "1"
