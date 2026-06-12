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

from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from bol.modules.m5_linguistic.engine import LinguisticEngine
from bol.modules.m4_policy.personality import ALL_PERSONALITIES

app = FastAPI()
logging.basicConfig(level=logging.INFO)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

GLOBAL_GOAL = None
AGENT_RESPONSE = "Ready."

class AgentChatRequest(BaseModel):
    text: str
    is_native_app: bool = False

@app.post("/api/agent/chat")
def agent_chat(req: AgentChatRequest):
    global GLOBAL_GOAL, AGENT_RESPONSE
    
    if "instagram" in req.text.lower() or "post" in req.text.lower():
        import datetime
        now = datetime.datetime.now()
        year, month, day = now.year, now.month, now.day
        
        slots_dir = get_slots_dir()
        target_slot = None
        for entry in slots_dir.iterdir():
            if entry.is_dir():
                target_slot = entry.name
                break
                
        caption = "Testing AHA Cloud Brain!"
        image_url = "https://picsum.photos/400/400" # fallback
        
        if target_slot:
            slot_dir = slots_dir / target_slot / str(year) / str(month)
            txt_path = slot_dir / "Texts" / f"{day}.txt"
            if txt_path.exists():
                try:
                    caption = txt_path.read_text(encoding="utf-8").strip()
                except:
                    pass
                
            img_dir = slot_dir / "Images"
            if img_dir.exists():
                for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
                    if (img_dir / f"{day}{ext}").exists():
                        image_url = f"https://aha-cloud-brain.onrender.com/api/vault/media/{target_slot}/{year}/{month}/{day}/image"
                        break
                        
        GLOBAL_GOAL = f"""
        Execute an Instagram Posting Workflow.
        Step 1: Click the Windows Start Menu, type "Chrome", and press Enter to open the browser.
        Step 2: Go to https://instagram.com.
        Step 3: Click the 'Create' (+) button to make a new post.
        Step 4: To get the image, open a NEW tab and go to: {image_url}. Right click the image and save it to the desktop as 'ig_post.jpg'.
        Step 5: Go back to the Instagram tab, click 'Select from computer', and select 'ig_post.jpg' from the Desktop.
        Step 6: Proceed to the caption screen and type exactly this caption: "{caption}"
        Step 7: Click Share.
        """
    else:
        GLOBAL_GOAL = req.text
        
    AGENT_RESPONSE = f"Executing: {req.text}"
    return {
        "status": "success", 
        "text": f"I am taking control to: {req.text}. I will use the cloud brain to analyze the screen.",
        "html": f"<p>I am taking control to: <b>{req.text}</b>. I will use the cloud brain to analyze the screen.</p>"
    }

@app.post("/api/agent/clear")
def agent_clear():
    global GLOBAL_GOAL
    GLOBAL_GOAL = None
    return {"status": "success"}

@app.websocket("/ws/agent")
async def websocket_endpoint(websocket: WebSocket):
    global GLOBAL_GOAL
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
                if model and GLOBAL_GOAL:
                    try:
                        b64_img = message.get("image")
                        image_bytes = base64.b64decode(b64_img)
                        img = Image.open(io.BytesIO(image_bytes))
                        width, height = img.size
                        
                        prompt = f"""
                        You are an AI agent controlling a Windows computer.
                        The user's overall goal is: "{GLOBAL_GOAL}"
                        
                        Look at the current screen. Determine the SINGLE next step required.
                        If the target app (e.g. Instagram, Chrome) is not visible, your next step should be clicking the Windows Start Menu or the Search bar so you can type the app name.
                        If you need to click something, return its bounding box in [ymin, xmin, ymax, xmax] format where values are 0-1000.
                        If you need to type something AFTER clicking, provide it in "type_text".
                        If the overall goal has been completely achieved, set "status" to "COMPLETE". Otherwise, set "status" to "IN_PROGRESS".
                        
                        Output ONLY a valid JSON object. Do not use markdown blocks. Example:
                        {{"box": [ymin, xmin, ymax, xmax], "type_text": "instagram", "status": "IN_PROGRESS"}}
                        """
                        
                        logging.info(f"Sending screenshot to Gemini Vision for goal: {GLOBAL_GOAL}...")
                        response = model.generate_content([img, prompt])
                        
                        # Parse the response
                        resp_text = response.text.strip()
                        if resp_text.startswith("```json"):
                            resp_text = resp_text[7:-3].strip()
                        elif resp_text.startswith("```"):
                            resp_text = resp_text[3:-3].strip()
                            
                        data = json.loads(resp_text)
                        box = data.get("box")
                        type_text = data.get("type_text", "")
                        status = data.get("status", "IN_PROGRESS")
                        
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
                            
                        if type_text:
                            # 3. Type text using linguistic engine
                            ling_engine = LinguisticEngine(personality=ALL_PERSONALITIES[0])
                            payload = ling_engine.prepare_payload(type_text)
                            seq = ling_engine.generate_keystroke_sequence(payload)
                            bridge.execute_keystroke_sequence(seq.events)
                            
                        if status == "COMPLETE":
                            logging.info(f"Goal COMPLETE: {GLOBAL_GOAL}")
                            GLOBAL_GOAL = None
                            
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

from fastapi import Form, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
# ── VAULT API ────────────────────────────────────────────────────────────────
from aha.storage_vault import vault_root
import os
from pathlib import Path

def get_slots_dir():
    # Use Downloads/aha/Slots as the base for custom slots
    base = vault_root() / "Slots"
    base.mkdir(parents=True, exist_ok=True)
    return base

@app.get("/api/vault/slots")
def list_vault_slots():
    slots_dir = get_slots_dir()
    slots = []
    for entry in slots_dir.iterdir():
        if entry.is_dir():
            slots.append(entry.name)
    return JSONResponse(content={"slots": sorted(slots)})

@app.post("/api/vault/slots")
async def create_vault_slot(slot_name: str = Form(...)):
    # Sanitize slot name
    safe_name = "".join([c for c in slot_name if c.isalnum() or c in (" ", "-", "_")]).strip()
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid slot name")
        
    slot_path = get_slots_dir() / safe_name
    slot_path.mkdir(parents=True, exist_ok=True)
    
    import datetime
    current_year = datetime.datetime.now().year
    
    # Generate multi-year structure in advance (current year + next 5 years)
    for year in range(current_year, current_year + 6):
        for month in range(1, 13):
            month_path = slot_path / str(year) / str(month)
            month_path.mkdir(parents=True, exist_ok=True)
            (month_path / "Texts").mkdir(exist_ok=True)
            (month_path / "Images").mkdir(exist_ok=True)
            (month_path / "Videos").mkdir(exist_ok=True)
    
    return JSONResponse(content={"success": True, "slot": safe_name})

@app.get("/api/vault/slot/{slot}/{year}/{month}")
def get_vault_slot_days(slot: str, year: int, month: int):
    slot_dir = get_slots_dir() / slot
    if not slot_dir.exists():
        raise HTTPException(status_code=404, detail="Slot not found")
        
    target_dir = slot_dir / str(year) / str(month)
        
    days = []
    # Calculate actual number of days in that month
    import calendar
    _, num_days = calendar.monthrange(year, month)
    for day in range(1, num_days + 1):
        has_text = False
        has_image = False
        has_video = False
        
        try:
            txt_path = target_dir / "Texts" / f"{day}.txt"
            if txt_path.exists() and txt_path.stat().st_size > 0:
                has_text = True
                
            # Check for any image extension
            for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
                img_path = target_dir / "Images" / f"{day}{ext}"
                if img_path.exists() and img_path.stat().st_size > 0:
                    has_image = True
                    break
                    
            # Check for video extensions
            for ext in [".mp4", ".mov", ".webm"]:
                vid_path = target_dir / "Videos" / f"{day}{ext}"
                if vid_path.exists() and vid_path.stat().st_size > 0:
                    has_video = True
                    break
        except Exception:
            pass
            
        days.append({
            "day": day,
            "has_text": has_text,
            "has_image": has_image,
            "has_video": has_video
        })
        
    return JSONResponse(content={"slot": slot, "days": days})

@app.post("/api/vault/upload/{slot}/{year}/{month}/{day}")
async def upload_vault_content(
    slot: str, 
    year: int,
    month: int,
    day: int,
    text: str = Form(None),
    image: UploadFile = File(None),
    video: UploadFile = File(None)
):
    slot_dir = get_slots_dir() / slot / str(year) / str(month)
    
    if not (get_slots_dir() / slot).exists():
        raise HTTPException(status_code=404, detail="Slot not found")
    
    saved = []
    
    if text is not None:
        txt_path = slot_dir / "Texts" / f"{day}.txt"
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        txt_path.write_text(text, encoding="utf-8")
        saved.append("text")
        
    if image is not None:
        # Clear existing images for this day first to avoid multiple extensions
        img_dir = slot_dir / "Images"
        img_dir.mkdir(parents=True, exist_ok=True)
        for p in img_dir.glob(f"{day}.*"):
            p.unlink()
            
        ext = os.path.splitext(image.filename)[1] or ".png"
        img_path = img_dir / f"{day}{ext}"
        content = await image.read()
        img_path.write_bytes(content)
        saved.append("image")
        
    if video is not None:
        vid_dir = slot_dir / "Videos"
        vid_dir.mkdir(parents=True, exist_ok=True)
        for p in vid_dir.glob(f"{day}.*"):
            p.unlink()
            
        ext = os.path.splitext(video.filename)[1] or ".mp4"
        vid_path = vid_dir / f"{day}{ext}"
        content = await video.read()
        vid_path.write_bytes(content)
        saved.append("video")
        
    return JSONResponse(content={"success": True, "saved": saved})

@app.get("/api/vault/content/{slot}/{year}/{month}/{day}")
def get_vault_content(slot: str, year: int, month: int, day: int):
    slot_dir = get_slots_dir() / slot / str(year) / str(month)
    if not slot_dir.exists():
        return JSONResponse(content={"text": "", "has_image": False, "has_video": False, "image_url": None, "video_url": None})
        
    text_content = ""
    txt_path = slot_dir / "Texts" / f"{day}.txt"
    if txt_path.exists():
        try:
            text_content = txt_path.read_text(encoding="utf-8")
        except Exception:
            pass
            
    has_image = False
    image_url = None
    for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
        img_path = slot_dir / "Images" / f"{day}{ext}"
        if img_path.exists():
            has_image = True
            image_url = f"/api/vault/media/{slot}/{year}/{month}/{day}/image"
            break
            
    has_video = False
    video_url = None
    for ext in [".mp4", ".mov", ".webm"]:
        vid_path = slot_dir / "Videos" / f"{day}{ext}"
        if vid_path.exists():
            has_video = True
            video_url = f"/api/vault/media/{slot}/{year}/{month}/{day}/video"
            break
            
    return JSONResponse(content={
        "text": text_content,
        "has_image": has_image,
        "image_url": image_url,
        "has_video": has_video,
        "video_url": video_url
    })

@app.get("/api/vault/media/{slot}/{year}/{month}/{day}/{media_type}")
def get_vault_media(slot: str, year: int, month: int, day: int, media_type: str):
    from fastapi.responses import FileResponse
    slot_dir = get_slots_dir() / slot / str(year) / str(month)
    
    if media_type == "image":
        for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
            p = slot_dir / "Images" / f"{day}{ext}"
            if p.exists():
                return FileResponse(p)
                
    elif media_type == "video":
        for ext in [".mp4", ".mov", ".webm"]:
            p = slot_dir / "Videos" / f"{day}{ext}"
            if p.exists():
                return FileResponse(p)
                
    raise HTTPException(status_code=404, detail="Media not found")
