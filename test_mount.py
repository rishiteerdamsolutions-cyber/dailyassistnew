import sys
import os
sys.path.insert(0, os.path.abspath('AHA-extension/backend'))
try:
    from ws.handler import handle_agent_session
    from api.license import router as ext_license_router
    print("Imports successful!")
except Exception as e:
    print(f"Import failed: {e}")
