from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import logging

# Import the new virtualized AccessibilityBridge
from bol.modules.m6_bridge.bridge import AccessibilityBridge
from bol.schemas.kinematic import Point2D

app = FastAPI()
logging.basicConfig(level=logging.INFO)

# We create a single global bridge for now. In a real multi-user SaaS, 
# you'd instantiate one per user/WebSocket session.
bridge = AccessibilityBridge()

@app.websocket("/ws/agent")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logging.info("Thin client connected.")
    try:
        while True:
            # Receive text payload from the client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "screenshot":
                logging.info("Received screenshot for processing.")
                
                # 1. Update the backend's virtual cursor position
                cursor_x = message.get("cursor_x", 0)
                cursor_y = message.get("cursor_y", 0)
                bridge.update_cursor(cursor_x, cursor_y)
                
                # 2. RUN AHA AGENT LOGIC HERE
                # image_data = message.get("image")
                # agent_plan = aha.analyze(image_data)
                # bol.execute(agent_plan)
                
                # For demonstration, let's pretend the AI decided to click something 
                # nearby using the bridge so we can see the queue working.
                # Remove this dummy logic when you plug in the real aha code!
                from backend.bol.schemas.bridge import ClickEvent, MouseButton
                dummy_click = ClickEvent(
                    target_x=cursor_x + 50, 
                    target_y=cursor_y + 50, 
                    button=MouseButton.LEFT,
                    pre_click_delay_ms=200
                )
                bridge.execute_click(dummy_click)
                
                # 3. Retrieve queued OS commands from the virtual bridge
                actions_to_execute = bridge.get_actions()
                
                # 4. Send them down to the Thin Client
                await websocket.send_text(json.dumps(actions_to_execute))
                
    except WebSocketDisconnect:
        logging.info("Thin client disconnected.")

@app.get("/")
def read_root():
    return {"status": "AHA Cloud Brain is running"}
