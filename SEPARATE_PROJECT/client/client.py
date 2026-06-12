import asyncio
import websockets
import json
import base64
import mss
import pyautogui
import time
import logging

logging.basicConfig(level=logging.INFO)

# Configuration
SERVER_URI = "ws://localhost:8000/ws/agent"
# In production, ask the user to input this, or load from config
SUBSCRIPTION_TOKEN = "your_token_here"

def capture_screen():
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        png_bytes = mss.tools.to_png(sct_img.rgb, sct_img.size)
        return base64.b64encode(png_bytes).decode('utf-8')

def execute_command(command):
    action = command.get("action")
    
    if action == "click":
        x = command.get("x")
        y = command.get("y")
        button = command.get("button", "left")
        delay_ms = command.get("pre_click_delay_ms", 0)
        
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
            
        logging.info(f"Clicking {button} at ({x}, {y})")
        pyautogui.click(x, y, button=button)
        
    elif action == "move_path":
        points = command.get("points", [])
        total_duration_ms = command.get("total_duration_ms", 0)
        logging.info(f"Moving mouse along path of {len(points)} points over {total_duration_ms}ms")
        
        if not points:
            return
            
        per_step_s = (total_duration_ms / len(points)) / 1000.0
        for pt in points:
            # We use moveTo instead of directly setting the OS cursor to respect pyautogui failsafes
            # For exact bezier kinematics, setting duration=per_step_s makes it smooth
            pyautogui.moveTo(pt["x"], pt["y"], duration=per_step_s)
            
    elif action == "type_sequence":
        events = command.get("events", [])
        logging.info(f"Typing sequence of {len(events)} keystrokes")
        for e in events:
            if e.get("delay_before_ms", 0) > 0:
                time.sleep(e["delay_before_ms"] / 1000.0)
                
            if e.get("is_correction"):
                pyautogui.press("backspace")
            else:
                # Use typewrite to handle characters accurately
                pyautogui.write(e.get("character", ""))
                
    elif action == "hotkey":
        keys = command.get("keys", [])
        logging.info(f"Executing hotkey: {keys}")
        pyautogui.hotkey(*keys)
        
    elif action == "scroll":
        num_steps = command.get("num_steps", 0)
        direction = command.get("direction", "down")
        step_delays_ms = command.get("step_delays_ms", [])
        stutter_map = command.get("stutter_map", {})
        
        clicks = -3 if direction == "down" else 3
        logging.info(f"Scrolling {direction} for {num_steps} steps")
        
        for i in range(num_steps):
            if i < len(step_delays_ms):
                time.sleep(step_delays_ms[i] / 1000.0)
                
            pyautogui.scroll(clicks)
            
            # Check for micro-stutter map using string keys since JSON maps integers to strings
            if str(i) in stutter_map:
                time.sleep(stutter_map[str(i)] / 1000.0)
    else:
        logging.warning(f"Unknown command action: {action}")

async def run_client():
    logging.info(f"Connecting to Cloud Brain at {SERVER_URI}...")
    try:
        async with websockets.connect(SERVER_URI) as websocket:
            logging.info("Connected successfully. Starting agent loop.")
            
            while True:
                logging.info("Capturing screen...")
                b64_img = capture_screen()
                
                # Get current physical cursor position to send back to the brain
                cursor_x, cursor_y = pyautogui.position()
                
                payload = {
                    "type": "screenshot",
                    "token": SUBSCRIPTION_TOKEN,
                    "image": b64_img,
                    "cursor_x": cursor_x,
                    "cursor_y": cursor_y
                }
                await websocket.send(json.dumps(payload))
                logging.info("Screenshot sent. Waiting for brain to process...")
                
                response = await websocket.recv()
                commands = json.loads(response)
                
                # Commands could be a list of actions or a single action
                if isinstance(commands, list):
                    for cmd in commands:
                        execute_command(cmd)
                else:
                    execute_command(commands)
                
                await asyncio.sleep(2)
                
    except websockets.exceptions.ConnectionClosed:
        logging.error("Connection closed by server.")
    except ConnectionRefusedError:
        logging.error("Could not connect to the server. Is the Cloud Brain running?")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    pyautogui.FAILSAFE = True
    asyncio.run(run_client())
