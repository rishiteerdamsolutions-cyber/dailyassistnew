import sys
if sys.platform == 'win32':
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import os
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import time

class PhysicalClickRequest(BaseModel):
    x: float
    y: float


# BOL Modules
from bol.modules.m1_timing.pool import TimingPoolGenerator
from bol.schemas.timing import TimingConfig
from bol.modules.m2_kinematic.bezier import BezierEngine
from bol.schemas.kinematic import Point2D
from bol.modules.m6_bridge.bridge import AccessibilityBridge
from bol.schemas.bridge import ClickEvent, MouseButton
from bol.modules.m4_policy.personality import ALL_PERSONALITIES
from bol.modules.m4_policy.engine import PolicyEngine
from bol.modules.m5_linguistic.engine import LinguisticEngine
try:
    from bol.modules.m6_bridge.hardware import HardwareMonitor
except ImportError:
    HardwareMonitor = None
from bol.modules.m7_lifecycle.calendar import CalendarEngine
from bol.modules.m7_lifecycle.void import VoidEngine
from datetime import date

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="BOL Framework Interface")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create web directory if it doesn't exist
os.makedirs("web", exist_ok=True)

# Mount the web directory for static files (CSS, JS)
app.mount("/static", StaticFiles(directory="web"), name="static")

@app.get("/")
def serve_index():
    return FileResponse("web/index.html")

@app.get("/companion")
def serve_companion():
    return FileResponse("web/companion.html")

@app.get("/api/timing")
def get_timing():
    config = TimingConfig(
        platform="demo",
        pool_size=100,
        min_latency_ms=200.0,
        max_latency_ms=4500.0,
        distribution_alpha=2.0,
        distribution_beta=5.0,
    )
    t0 = time.time()
    values = TimingPoolGenerator.generate_pool(config)
    gen_time = (time.time() - t0) * 1000
    
    return JSONResponse(content={
        "pool_size": len(values),
        "min_val": min(values),
        "max_val": max(values),
        "gen_time_ms": gen_time,
        "sample": values[:20]
    })

@app.get("/api/kinematic")
def get_kinematic():
    start = Point2D(x=100.0, y=400.0)
    end = Point2D(x=900.0, y=200.0)
    distance = start.distance_to(end)

    cp = BezierEngine.generate_control_points(start, end)
    trajectory = BezierEngine.sample_trajectory(cp, num_steps=60)
    duration = BezierEngine.calculate_duration_ms(distance)
    
    return JSONResponse(content={
        "start": {"x": start.x, "y": start.y},
        "end": {"x": end.x, "y": end.y},
        "distance": distance,
        "duration_ms": duration,
        "control_p1": {"x": cp.p1.x, "y": cp.p1.y},
        "control_p2": {"x": cp.p2.x, "y": cp.p2.y},
        "trajectory": [{"x": p.x, "y": p.y} for p in trajectory]
    })

@app.get("/api/policy")
def get_policy():
    engine = PolicyEngine()
    session = engine.initialize_session()
    
    states = []
    for _ in range(15):
        state = engine.get_current_state()
        duration_ms = engine.get_state_duration_ms()
        states.append({"state": state.value, "duration_ms": duration_ms})
        if state.value == "exiting":
            break
        engine.advance_state()
        
    return JSONResponse(content={
        "personality": session.personality.name,
        "states": states
    })

@app.get("/api/linguistic")
def get_linguistic():
    sample_text = "AI is transforming how we build software."
    ling = LinguisticEngine(
        personality=ALL_PERSONALITIES[0], # Distracted Academic
        history_db_path=None,
    )
    payload = ling.prepare_payload(sample_text)
    seq = ling.generate_keystroke_sequence(payload)
    
    events = []
    for e in seq.events:
        events.append({
            "char": e.character,
            "delay_ms": e.delay_before_ms,
            "is_typo": e.is_typo,
            "is_correction": e.is_correction
        })
        
    return JSONResponse(content={
        "text": sample_text,
        "total_duration_ms": seq.total_duration_ms,
        "wpm_start": seq.effective_wpm_start,
        "wpm_end": seq.effective_wpm_end,
        "events": events
    })

@app.get("/api/lifecycle")
def get_lifecycle():
    engine = CalendarEngine(timezone="Asia/Kolkata")
    decision = engine.is_posting_allowed()
    void_engine = VoidEngine(engine.state)
    voids = void_engine.generate_void_schedule(months_ahead=3)
    
    void_list = []
    for v in voids:
        void_list.append({
            "start": str(v.start_date),
            "end": str(v.end_date),
            "duration": v.duration_days,
            "reason": v.reason.value
        })
        
    return JSONResponse(content={
        "today": str(date.today()),
        "day_type": decision.day_type.value,
        "should_execute": decision.should_execute,
        "reason": decision.reason,
        "scheduled_voids": void_list
    })

@app.get("/api/hardware")
def get_hardware():
    if not HardwareMonitor:
        return JSONResponse(content={"error": "psutil not installed"}, status_code=500)
    
    monitor = HardwareMonitor()
    samples = []
    for _ in range(5):
        jitter = monitor.get_jitter()
        samples.append({
            "cpu_percent": jitter.snapshot.cpu_percent,
            "ram_percent": jitter.snapshot.ram_percent,
            "jitter_ms": jitter.computed_delay_ms
        })
        
    return JSONResponse(content={"samples": samples})

class PhysicalClickRequest(BaseModel):
    x: float
    y: float
    width: float = 0.0
    height: float = 0.0

@app.post("/api/kinematic/physical_click")
def physical_click(req: PhysicalClickRequest):
    import random
    bridge = AccessibilityBridge()
    start_pos = bridge.get_cursor_position()
    
    # 1. Off-Center Click (Sloppy Aim)
    # Calculate a random target point inside the button, avoiding the absolute edges.
    padding_x = req.width * 0.2 if req.width else 0
    padding_y = req.height * 0.2 if req.height else 0
    
    target_x = req.x
    target_y = req.y
    if req.width and req.height:
        # req.x and req.y are the center of the button right now.
        # offset by random amount
        offset_x = random.uniform(-req.width/2 + padding_x, req.width/2 - padding_x)
        offset_y = random.uniform(-req.height/2 + padding_y, req.height/2 - padding_y)
        target_x += offset_x
        target_y += offset_y
        
    final_target = Point2D(x=target_x, y=target_y)
    
    # Helper to move cursor with Bezier
    def _move_to(dest: Point2D, steps=30):
        current = bridge.get_cursor_position()
        dist = current.distance_to(dest)
        if dist < 2.0:
            return
        cp = BezierEngine.generate_control_points(current, dest)
        traj = BezierEngine.sample_trajectory(cp, num_steps=steps)
        dur = BezierEngine.calculate_duration_ms(dist)
        bridge.execute_movement(traj, dur)

    # 2. Hesitation Looping
    # 20% chance to do a random wiggle/loop before starting
    if random.random() < 0.20:
        loop_target = Point2D(
            x=start_pos.x + random.uniform(-100, 100),
            y=start_pos.y + random.uniform(-100, 100)
        )
        _move_to(loop_target, steps=15)
        time.sleep(random.uniform(0.1, 0.4))
        
    current_pos = bridge.get_cursor_position()
    distance_to_target = current_pos.distance_to(final_target)
    
    # 3. Segmented Journey
    # If the distance is long, pick a waypoint
    if distance_to_target > 400:
        waypoint_ratio = random.uniform(0.4, 0.7)
        waypoint_x = current_pos.x + (final_target.x - current_pos.x) * waypoint_ratio
        waypoint_y = current_pos.y + (final_target.y - current_pos.y) * waypoint_ratio
        
        # Add perpendicular variance so it's not a straight line to the target
        waypoint_x += random.uniform(-100, 100)
        waypoint_y += random.uniform(-100, 100)
        
        _move_to(Point2D(x=waypoint_x, y=waypoint_y), steps=25)
        # Human pauses to look at the screen
        time.sleep(random.uniform(0.15, 0.45))
        
    # 4. Pre-target Wobble (Micro-Correction)
    # Aim slightly off the target first
    wobble_x = final_target.x + random.uniform(-30, 30)
    wobble_y = final_target.y + random.uniform(-30, 30)
    
    _move_to(Point2D(x=wobble_x, y=wobble_y), steps=25)
    time.sleep(random.uniform(0.05, 0.15)) # tiny pause to realize we missed
    
    # Final precise move to target
    _move_to(final_target, steps=10)

    # Execute physical click
    click_event = ClickEvent(
        target_x=int(final_target.x),
        target_y=int(final_target.y),
        button=MouseButton.LEFT,
        pre_click_delay_ms=random.uniform(100, 250)
    )
    bridge.execute_click(click_event)
    
    return {"status": "success", "x": target_x, "y": target_y}

class VisualScanRequest(BaseModel):
    target_word: str

@app.post("/api/visual/scan_text")
def visual_scan(req: VisualScanRequest):
    import cv2
    import base64
    from bol.modules.m3_visual.capture import ScreenCapturePipeline
    from bol.modules.m3_visual.ocr import OCREngine

    pipeline = ScreenCapturePipeline()
    ocr = OCREngine(confidence_threshold=30)
    
    # Take screenshot
    capture_meta, img_bgr = pipeline.capture_full_screen()
    
    # Search for word
    bboxes = ocr.find_text_on_screen(img_bgr, req.target_word)
    
    # Draw red rectangles
    for box in bboxes:
        top_left = (box.x, box.y)
        bottom_right = (box.x + box.width, box.y + box.height)
        cv2.rectangle(img_bgr, top_left, bottom_right, (0, 0, 255), 4)
        
    # Encode image to Base64
    _, buffer = cv2.imencode('.jpg', img_bgr)
    img_base64 = base64.b64encode(buffer).decode('utf-8')
    
    return {
        "status": "success",
        "matches_found": len(bboxes),
        "image_data": f"data:image/jpeg;base64,{img_base64}"
    }

class FindAndClickRequest(BaseModel):
    target_word: str

@app.post("/api/orchestrator/find_and_click")
def find_and_click(req: FindAndClickRequest):
    import re
    from bol.modules.m3_visual.capture import ScreenCapturePipeline
    from bol.modules.m3_visual.ocr import OCREngine

    pipeline = ScreenCapturePipeline()
    ocr = OCREngine(confidence_threshold=30)
    
    # 1. Take screenshot
    capture_meta, img_bgr = pipeline.capture_full_screen()
    
    # Check for index syntax like "Submit[2]" or "Submit(2)"
    search_word = req.target_word.strip()
    target_idx = 0
    match = re.search(r'[\[\(](\d+)[\]\)]$', search_word)
    if match:
        target_idx = int(match.group(1)) - 1 # 1-indexed to 0-indexed
        search_word = search_word[:match.start()].strip()
    
    # 2. Find word via OCR
    bboxes = ocr.find_text_on_screen(img_bgr, search_word)
    
    if not bboxes:
        return {"status": "error", "message": f"Could not find word '{search_word}' on screen."}
        
    # Sort bounding boxes top-to-bottom, left-to-right (bucket y into lines of 15px)
    bboxes = sorted(bboxes, key=lambda b: (b.y // 15, b.x))
    
    if target_idx >= len(bboxes):
         return {"status": "error", "message": f"Found {len(bboxes)} instances of '{search_word}', but requested index {target_idx + 1}."}
         
    # Pick the requested match
    box = bboxes[target_idx]
    
    # 3. Trigger Kinematic physical click (we use the center of the bounding box)
    click_req = PhysicalClickRequest(
        x=box.x + (box.width / 2.0),
        y=box.y + (box.height / 2.0),
        width=float(box.width),
        height=float(box.height)
    )
    
    # Execute the physical click logic we already built!
    physical_click(click_req)
    
    return {"status": "success", "message": f"Clicked '{search_word}' (Instance {target_idx + 1})"}

from typing import List
import time

class ChainClickRequest(BaseModel):
    target_words: List[str]

@app.post("/api/orchestrator/chain_click")
def chain_click(req: ChainClickRequest):
    import re
    from bol.modules.m3_visual.capture import ScreenCapturePipeline
    from bol.modules.m3_visual.ocr import OCREngine

    pipeline = ScreenCapturePipeline()
    ocr = OCREngine(confidence_threshold=30)
    
    results = []
    
    for word in req.target_words:
        original_word = word.strip()
        if not original_word:
            continue
            
        # Check for typing command e.g., Type 'hello' or Type "hello"
        if original_word.lower().startswith("type "):
            text_to_type = original_word[5:].strip()
            # Remove surrounding quotes (including Mac smart quotes)
            if len(text_to_type) >= 2 and text_to_type[0] in "'\"“”‘’" and text_to_type[-1] in "'\"“”‘’":
                text_to_type = text_to_type[1:-1]
                
            if text_to_type:
                # Biologically type the text!
                from bol.modules.m5_linguistic.engine import LinguisticEngine
                from bol.modules.m4_policy.personality import ALL_PERSONALITIES
                from bol.modules.m6_bridge.bridge import AccessibilityBridge
                
                # We use the default personality (or could be parameterized later)
                ling = LinguisticEngine(personality=ALL_PERSONALITIES[0])
                payload = ling.prepare_payload(text_to_type)
                seq = ling.generate_keystroke_sequence(payload)
                
                bridge = AccessibilityBridge()
                bridge.execute_keystroke_sequence(seq.events)
                
                results.append({"word": original_word, "status": "success", "message": f"Typed {len(text_to_type)} chars"})
            else:
                results.append({"word": original_word, "status": "error", "message": "Empty text to type"})
                
            time.sleep(1.0) # Pause before next action
            continue

        search_word = original_word
        target_idx = 0
        match = re.search(r'[\[\(](\d+)[\]\)]$', search_word)
        if match:
            target_idx = int(match.group(1)) - 1
            search_word = search_word[:match.start()].strip()
            
        # 1 & 2. Take screenshot and find word (with retries for page load)
        max_retries = 4
        bboxes = []
        for attempt in range(max_retries):
            capture_meta, img_bgr = pipeline.capture_full_screen()
            bboxes = ocr.find_text_on_screen(img_bgr, search_word)
            if len(bboxes) > target_idx:
                break
            # If not found enough, wait and try again (page might be loading)
            time.sleep(1.5)
            
        if not bboxes:
            results.append({"word": original_word, "status": "error", "message": "Not found on screen after retries."})
            continue # Try the next word in the chain
            
        # Sort bounding boxes top-to-bottom, left-to-right (bucket y into lines of 15px)
        bboxes = sorted(bboxes, key=lambda b: (b.y // 15, b.x))
        
        if target_idx >= len(bboxes):
             results.append({"word": original_word, "status": "error", "message": f"Only found {len(bboxes)} instances."})
             continue
             
        # Pick the requested match
        box = bboxes[target_idx]
        
        # 3. Trigger Kinematic physical click
        click_req = PhysicalClickRequest(
            x=box.x + (box.width / 2.0),
            y=box.y + (box.height / 2.0),
            width=float(box.width),
            height=float(box.height)
        )
        
        physical_click(click_req)
        results.append({"word": original_word, "status": "success"})
        
        # 4. Pause to let UI react before next screenshot
        time.sleep(1.0)
    
    return {"status": "success", "chain_results": results}

# --- Policy Engine (Personalities) Endpoints ---

@app.get("/api/policy/personalities")
def get_personalities():
    from bol.modules.m4_policy.personality import ALL_PERSONALITIES
    return {
        "status": "success",
        "personalities": [
            {
                "name": p.name,
                "description": p.description,
                "base_wpm_min": p.base_wpm_min,
                "base_wpm_max": p.base_wpm_max,
                "typo_rate_modifier": p.typo_rate_modifier,
                "fatigue_rate": p.fatigue_rate,
                "timing_modifier": p.timing_modifier
            } for p in ALL_PERSONALITIES
        ]
    }

class SimulateTypingRequest(BaseModel):
    personality_name: str
    text: str

@app.post("/api/policy/simulate_typing")
def simulate_policy_typing(req: SimulateTypingRequest):
    from bol.modules.m4_policy.personality import ALL_PERSONALITIES
    from bol.modules.m5_linguistic.engine import LinguisticEngine
    
    # 1. Find the selected personality
    profile = next((p for p in ALL_PERSONALITIES if p.name == req.personality_name), None)
    if not profile:
        return {"status": "error", "message": "Personality not found"}
        
    # 2. Generate keystrokes using their specific math
    engine = LinguisticEngine(personality=profile)
    payload = engine.prepare_payload(req.text)
    seq = engine.generate_keystroke_sequence(payload)
    
    time_mult = profile.timing_modifier
    events_data = []
    for e in seq.events:
        events_data.append({
            "character": e.character,
            "delay_before_ms": e.delay_before_ms * time_mult
        })
    
    return {
        "status": "success",
        "personality": profile.name,
        "events": events_data,
        "stats": {
            "start_wpm": round(seq.effective_wpm_start, 1),
            "end_wpm": round(seq.effective_wpm_end, 1),
            "fatigue_drop_wpm": round(seq.effective_wpm_start - seq.effective_wpm_end, 1),
            "simulated_typos": seq.typo_count,
            "total_time_seconds": round(seq.total_duration_ms / 1000.0, 2)
        }
    }

# --- Lifecycle Engine Endpoints ---

class EvaluateLifecycleRequest(BaseModel):
    lifecycle_mode_enabled: bool
    spoof_date: str = "" # e.g. "2026-05-24" (Sunday)
    spoof_hour: int = -1

@app.post("/api/lifecycle/evaluate")
def evaluate_lifecycle(req: EvaluateLifecycleRequest):
    from bol.modules.m7_lifecycle.controller import LifecycleController
    from bol.config import BOLConfig
    from datetime import date
    
    # 1. If mode is off, instantly approve (Manual Override)
    if not req.lifecycle_mode_enabled:
        return {
            "status": "success",
            "decision": True,
            "reason": "Execution: APPROVED (Manual Override Active)",
            "day_type": "N/A"
        }
        
    # 2. Parse spoof values
    check_date = None
    if req.spoof_date:
        try:
            check_date = date.fromisoformat(req.spoof_date)
        except ValueError:
            pass
            
    check_hour = req.spoof_hour if req.spoof_hour >= 0 else None
    
    # 3. Evaluate using the Lifecycle Engine
    config = BOLConfig(tenant_id="sandbox", data_dir="data")
    controller = LifecycleController(config)
    decision = controller.should_execute_today(check_date=check_date, check_hour=check_hour)
    
    # 4. Return the biological decision
    prefix = "[APPROVED]" if decision.should_execute else "[DENIED]"
    return {
        "status": "success",
        "decision": decision.should_execute,
        "reason": f"{prefix} Reason: {decision.reason}",
        "day_type": decision.day_type.value
    }

# --- Autonomous Companion Endpoints ---

from bol.config import get_config
from bol.modules.m8_orchestrator.agent import AutonomousCompanion

# Global singleton for the agent session
_agent_instance = None

def get_agent():
    global _agent_instance
    if _agent_instance is None:
        config = get_config()
        _agent_instance = AutonomousCompanion(config)
    return _agent_instance

class AgentChatRequest(BaseModel):
    text: str

@app.post("/api/agent/chat")
def agent_chat(req: AgentChatRequest):
    try:
        agent = get_agent()
        result = agent.step(user_message=req.text)
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/agent/resume")
def agent_resume(req: AgentChatRequest):
    try:
        agent = get_agent()
        result = agent.step(user_message="User has completed the manual step. Please resume workflow.")
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}
