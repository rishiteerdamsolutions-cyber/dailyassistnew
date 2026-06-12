import cv2
import sys
import os
sys.path.append('/Users/nandagiriaditya/GEMINI/ARTIFICIALHUMANAGENT')
from bol.modules.m3_visual.capture import _capture_screen
from bol.modules.m3_visual.vision_buttons import VisionButtonLibrary
import pytesseract

def main():
    print("Taking screenshot...")
    screen = _capture_screen()
    print(f"Screenshot size: {screen.shape}")
    
    lib = VisionButtonLibrary()
    
    print("Testing template matching for instagram_new_post_icon...")
    matches = lib.find_all("instagram_new_post_icon", screen, min_confidence=0.6)
    
    print(f"Found {len(matches)} matches.")
    for m in matches:
        print(f"Match: {m.bbox.center_x}, {m.bbox.center_y} (conf: {m.confidence:.2f})")
        
    print("\nTesting OCR inverted...")
    gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
    normal_text = pytesseract.image_to_string(gray, config='--psm 11').lower()
    inverted = cv2.bitwise_not(gray)
    inverted_text = pytesseract.image_to_string(inverted, config='--psm 11').lower()
    
    print("Normal OCR contains 'create':", 'create' in normal_text)
    print("Inverted OCR contains 'create':", 'create' in inverted_text)

if __name__ == '__main__':
    main()
