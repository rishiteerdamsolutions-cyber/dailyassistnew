import sys
import os

with open('server.py', 'r') as f:
    content = f.read()

patch = """
# --- AHA Extension Backend Integration ---
import sys
import os
sys.path.insert(0, os.path.abspath('AHA-extension/backend'))
try:
    from ws.handler import handle_agent_session
    from api.license import router as ext_license_router
    from api.webhooks import router as ext_webhooks_router
    
    app.websocket("/ws/agent")(handle_agent_session)
    app.include_router(ext_license_router)
    app.include_router(ext_webhooks_router)
    print("AHA Extension Backend integrated successfully.")
except ImportError as e:
    print(f"Failed to integrate AHA Extension Backend: {e}")

# Create web directory if it doesn't exist
"""

new_content = content.replace("# Create web directory if it doesn't exist\n", patch)

with open('server.py', 'w') as f:
    f.write(new_content)
