#!/usr/bin/env python3
import time
import sys

from bol.modules.m6_bridge.bridge import AccessibilityBridge
from bol.modules.m2_kinematic.bezier import BezierEngine
from bol.modules.m2_kinematic.scroll import ScrollEngine
from bol.schemas.kinematic import Point2D, ScrollDirection
from bol.modules.m5_linguistic.engine import LinguisticEngine
from bol.modules.m4_policy.personality import ALL_PERSONALITIES

def print_countdown(seconds: int):
    print(f"\n[!] LIVE EXECUTION STARTING IN {seconds} SECONDS.")
    print("[!] IMPORTANT: Please click inside the 'Target Sandbox' text area now and leave your mouse there.")
    for i in range(seconds, 0, -1):
        print(f"    {i}...")
        time.sleep(1)
    print("\n[!] EXECUTING PHYSICAL ACTIONS NOW...\n")

def main():
    bridge = AccessibilityBridge()
    
    print_countdown(5)
    
    # 1. Kinematic: Move the mouse in a natural curve
    print("[*] 1. Executing Kinematic Mouse Movement...")
    start_pos = bridge.get_cursor_position()
    end_pos = Point2D(x=start_pos.x + 200, y=start_pos.y + 100)
    
    cp = BezierEngine.generate_control_points(start_pos, end_pos)
    trajectory = BezierEngine.sample_trajectory(cp, num_steps=40)
    distance = start_pos.distance_to(end_pos)
    duration = BezierEngine.calculate_duration_ms(distance)
    
    bridge.execute_movement(trajectory, duration)
    
    # Wait a moment
    time.sleep(1)
    
    # 2. Scroll: Perform a sinusoidal scroll
    print("[*] 2. Executing Sinusoidal Scroll Physics...")
    scroll_engine = ScrollEngine()
    profile = scroll_engine.generate_scroll_profile(distance_px=500, direction=ScrollDirection.DOWN)
    bridge.execute_scroll(profile)
    
    # Scroll back up
    time.sleep(0.5)
    profile_up = scroll_engine.generate_scroll_profile(distance_px=500, direction=ScrollDirection.UP)
    bridge.execute_scroll(profile_up)
    
    # 3. Linguistic: Type with typos and fatigue
    print("[*] 3. Executing Linguistic Keystrokes with Typo Correction...")
    text_to_type = "Hello! This is the BOL agent taking physical control of the keyboard. I am making typos and correcting them naturally, just like a human."
    
    ling = LinguisticEngine(
        personality=ALL_PERSONALITIES[0], # Distracted Academic
        history_db_path=None,
    )
    payload = ling.prepare_payload(text_to_type)
    seq = ling.generate_keystroke_sequence(payload)
    
    # This physically types the keys while printing live debug information!
    for i, event in enumerate(seq.events):
        char_display = "SPACE" if event.character == " " else event.character
        action = "BACKSPACE" if event.is_correction else f"Typing '{char_display}'"
        
        # Print the delay we are about to take
        print(f"[{i:3d}] Waiting {event.delay_before_ms:5.1f}ms -> {action}")
        
        if event.delay_before_ms > 0:
            time.sleep(event.delay_before_ms / 1000.0)
            
        if event.is_correction:
            bridge._input.press_key("backspace")
        else:
            bridge._input.type_character(event.character)

    
    print("\n[✓] LIVE EXECUTION COMPLETE.")

if __name__ == "__main__":
    main()
