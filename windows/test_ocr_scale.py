from bol.modules.m3_visual.capture import ScreenCapturePipeline
import pytesseract
from pytesseract import Output
from PIL import Image
import cv2

pipeline = ScreenCapturePipeline()
_, img_bgr = pipeline.capture_full_screen()

# Scale image by 2x
scaled = cv2.resize(img_bgr, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

pil_image = Image.fromarray(scaled[:, :, ::-1])
data = pytesseract.image_to_data(pil_image, output_type=Output.DICT, config='--psm 11')

count = 0
for i in range(len(data["text"])):
    text = str(data["text"][i]).strip().lower()
    if 'post' in text:
        count += 1
        print(f"Scaled found: '{text}' at {data['left'][i]//2}, {data['top'][i]//2} conf={data['conf'][i]}")

if count == 0:
    print("Still no post found with scaling.")
