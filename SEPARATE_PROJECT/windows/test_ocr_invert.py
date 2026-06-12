import cv2
from bol.modules.m3_visual.capture import ScreenCapturePipeline
from bol.modules.m3_visual.ocr import OCREngine
from PIL import Image
import pytesseract
from pytesseract import Output

pipeline = ScreenCapturePipeline()
ocr = OCREngine(confidence_threshold=30)
_, img_bgr = pipeline.capture_full_screen()

# Try grayscale + contrast + invert
gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
# Invert it
inverted = cv2.bitwise_not(gray)

pil_image = Image.fromarray(inverted)
data = pytesseract.image_to_data(pil_image, output_type=Output.DICT)

count = 0
for i in range(len(data["text"])):
    text = str(data["text"][i]).strip().lower()
    if 'post' in text:
        count += 1
        print(f"Inverted found: '{text}' at {data['left'][i]}, {data['top'][i]} conf={data['conf'][i]}")

if count == 0:
    print("Still no post found in inverted image.")
