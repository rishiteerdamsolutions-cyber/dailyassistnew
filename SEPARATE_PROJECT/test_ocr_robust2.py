import cv2
from bol.modules.m3_visual.capture import ScreenCapturePipeline
from bol.modules.m3_visual.ocr import OCREngine
import pytesseract
from pytesseract import Output
from PIL import Image

pipeline = ScreenCapturePipeline()
_, img_bgr = pipeline.capture_full_screen()

scaled = cv2.resize(img_bgr, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
rgb = scaled[:, :, ::-1]

gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
_, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
inverted = cv2.bitwise_not(thresh)

passes = [
    (Image.fromarray(rgb), "Normal"),
    (Image.fromarray(thresh), "Thresh"),
    (Image.fromarray(inverted), "Inverted"),
]

found = 0
for pil_img, name in passes:
    data = pytesseract.image_to_data(pil_img, output_type=Output.DICT, config='--psm 11')
    for i in range(len(data["text"])):
        conf = int(data["conf"][i])
        text = str(data["text"][i]).strip().lower()
        if 'post' in text:
            print(f"[{name}] Found '{text}' at conf={conf}")
            found += 1

if found == 0:
    print("Nothing found.")
