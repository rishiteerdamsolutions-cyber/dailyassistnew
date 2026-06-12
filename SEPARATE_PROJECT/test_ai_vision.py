#!/usr/env/bin python3
import time
from bol.config import get_config
from bol.modules.m3_visual.cortex import VisualCortex

def main():
    print("[*] Initializing Configuration...")
    config = get_config()
    
    # Ensure Gemini is used
    config.vision_provider = "gemini"
    
    if not config.gemini_api_key:
        print("[!] Warning: BOL_GEMINI_API_KEY is not set in your .env file or environment!")
        return

    print("[*] Initializing Visual Cortex (This will load Tesseract and Gemini Engine)...")
    cortex = VisualCortex(config)
    
    if not cortex._ai_vision.is_enabled:
        print("[!] AI Vision Engine failed to enable. Check google-generativeai installation and API key.")
        return

    intent = "I want to search for flights"
    print(f"\n[*] Testing AI Vision with intent: '{intent}'")
    print("[*] Please bring a browser with a travel booking page into view.")
    print("[*] Waiting 5 seconds before capture...")
    
    for i in range(5, 0, -1):
        print(f"    {i}...")
        time.sleep(1)

    print("\n[*] Capturing screen and querying Gemini...")
    target = cortex.locate_by_intent(intent)
    
    if target:
        print(f"\n[✓] SUCCESS: Found target! You should click at ({target.click_x}, {target.click_y})")
    else:
        print("\n[X] FAILED: Could not find target for the given intent on screen.")

if __name__ == "__main__":
    main()
