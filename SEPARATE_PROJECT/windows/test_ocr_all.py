from bol.modules.m3_visual.capture import ScreenCapturePipeline
from bol.modules.m3_visual.ocr import OCREngine

pipeline = ScreenCapturePipeline()
ocr = OCREngine(confidence_threshold=10) # Drop confidence to 10 to see EVERYTHING
_, img_bgr = pipeline.capture_full_screen()
res = ocr.extract_text(img_bgr)

for w in res.words:
    if len(w.text.strip()) > 2:
        print(f"'{w.text}' conf={w.confidence} pos=({w.bounding_box.x}, {w.bounding_box.y})")
