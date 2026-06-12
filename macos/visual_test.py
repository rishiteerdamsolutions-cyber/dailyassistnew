import cv2
import sys
from bol.modules.m3_visual.capture import ScreenCapturePipeline
from bol.modules.m3_visual.ocr import OCREngine

def main(target_word: str):
    print(f"Taking physical screenshot to search for: '{target_word}'...")
    
    pipeline = ScreenCapturePipeline()
    ocr = OCREngine()
    
    # 1. Take a physical screenshot of the monitor
    capture_meta, img_bgr = pipeline.capture_full_screen()
    print(f"Captured screen resolution: {capture_meta.width}x{capture_meta.height}")
    
    # 2. Run OCR to find the word
    print("Running Tesseract OCR Computer Vision...")
    bboxes = ocr.find_text_on_screen(img_bgr, target_word)
    
    if not bboxes:
        print(f"Could not find the word '{target_word}' on the screen.")
        return
        
    print(f"SUCCESS: Found {len(bboxes)} occurrences of '{target_word}'!")
    
    # 3. Draw red rectangles around found text
    for box in bboxes:
        top_left = (box.x, box.y)
        bottom_right = (box.x + box.width, box.y + box.height)
        # BGR color for Red is (0, 0, 255)
        cv2.rectangle(img_bgr, top_left, bottom_right, (0, 0, 255), 4) 
        
    # 4. Save the resulting image
    out_file = "vision_test_result.png"
    cv2.imwrite(out_file, img_bgr)
    print(f"\nSaved vision analysis to: {out_file}")
    print("Open this file in Finder to see what the Visual Agent sees!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: .venv/bin/python visual_test.py <word_to_find>")
    else:
        main(sys.argv[1])
