"""PyInstaller runtime hook — mark retail builds (no dev license bypass)."""
import os

os.environ["AHA_RETAIL_BUILD"] = "1"
# Tier-1-only launch: deterministic social/local flows; Tier-2 BYOK ships later.
os.environ.setdefault("AHA_TIER1_ONLY", "1")
