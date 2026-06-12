from bol.modules.m3_visual.capture import ScreenCapturePipeline
import pytesseract
from pytesseract import Output
from PIL import Image

pipeline = ScreenCapturePipeline()
_, img_bgr = pipeline.capture_full_screen()

pil_image = Image.fromarray(img_bgr[:, :, ::-1])
data = pytesseract.image_to_data(pil_image, output_type=Output.DICT, config='--psm 11')

count = 0
for i in range(len(data["text"])):
    text = str(data["text"][i]).strip().lower()
    if 'post' in text:
        count += 1
        print(f"PSM 11 found: '{text}' at {data['left'][i]}, {data['top'][i]} conf={data['conf'][i]}")

if count == 0:
    print("Still no post found with PSM 11.")
