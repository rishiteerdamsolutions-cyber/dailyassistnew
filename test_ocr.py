from bol.modules.m3_visual.capture import ScreenCapturePipeline
from bol.modules.m3_visual.ocr import OCREngine

pipeline = ScreenCapturePipeline()
ocr = OCREngine(confidence_threshold=30)
_, img_bgr = pipeline.capture_full_screen()
res = ocr.extract_text(img_bgr)

print(f"Total words found: {len(res.words)}")
post_words = [w for w in res.words if 'post' in w.text.lower()]
print(f"Post words found: {len(post_words)}")
for w in post_words:
    print(f" - '{w.text}' at {w.bounding_box}")
