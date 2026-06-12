from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import logging

# Import the new virtualized AccessibilityBridge
from bol.modules.m6_bridge.bridge import AccessibilityBridge
import os
import io
import base64
from PIL import Image
from dotenv import load_dotenv
import google.generativeai as genai

from bol.schemas.kinematic import Point2D
from bol.schemas.bridge import ClickEvent, MouseButton
from bol.modules.m2_kinematic.bezier import BezierEngine

app = FastAPI()
logging.basicConfig(level=logging.INFO)

load_dotenv()
api_key = os.environ.get("BOL_GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    # Using 1.5-flash for speed, you can change to pro if needed
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None
    logging.warning("BOL_GEMINI_API_KEY not found in .env. LLM will not work.")

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
                if model:
                    try:
                        b64_img = message.get("image")
                        image_bytes = base64.b64decode(b64_img)
                        img = Image.open(io.BytesIO(image_bytes))
                        width, height = img.size
                        
                        prompt = (
                            "Find the Spotlight search icon (magnifying glass) on the top right menu bar. "
                            "Return its bounding box in [ymin, xmin, ymax, xmax] format where values are 0-1000. "
                            "Output ONLY a valid JSON object like {\"box\": [ymin, xmin, ymax, xmax]} "
                            "Do not use markdown formatting like ```json."
                        )
                        
                        logging.info("Sending screenshot to Gemini Vision...")
                        response = model.generate_content([img, prompt])
                        
                        # Parse the response
                        resp_text = response.text.strip()
                        if resp_text.startswith("```json"):
                            resp_text = resp_text[7:-3].strip()
                        elif resp_text.startswith("```"):
                            resp_text = resp_text[3:-3].strip()
                            
                        data = json.loads(resp_text)
                        box = data.get("box")
                        
                        if box and len(box) == 4:
                            ymin, xmin, ymax, xmax = box
                            
                            # Convert 0-1000 normalized to pixel coordinates
                            target_x = ((xmin + xmax) / 2) * (width / 1000)
                            target_y = ((ymin + ymax) / 2) * (height / 1000)
                            
                            logging.info(f"Gemini found target at ({target_x}, {target_y})")
                            
                            start_pos = bridge.get_cursor_position()
                            end_pos = Point2D(x=target_x, y=target_y)
                            distance = start_pos.distance_to(end_pos)
                            
                            if distance > 10:
                                # 1. Smoothly move to target
                                cp = BezierEngine.generate_control_points(start_pos, end_pos)
                                trajectory = BezierEngine.sample_trajectory(cp, num_steps=40)
                                duration = BezierEngine.calculate_duration_ms(distance)
                                bridge.execute_movement(trajectory, duration)
                            
                            # 2. Click target
                            click = ClickEvent(
                                target_x=target_x, 
                                target_y=target_y, 
                                button=MouseButton.LEFT,
                                pre_click_delay_ms=200
                            )
                            bridge.execute_click(click)
                    except Exception as e:
                        logging.error(f"Failed to process Gemini vision loop: {e}")
                
                # 3. Retrieve queued OS commands from the virtual bridge
                actions_to_execute = bridge.get_actions()
                
                # 4. Send them down to the Thin Client
                await websocket.send_text(json.dumps(actions_to_execute))
                
    except WebSocketDisconnect:
        logging.info("Thin client disconnected.")

@app.get("/")
def read_root():
    return {"status": "AHA Cloud Brain is running"}
