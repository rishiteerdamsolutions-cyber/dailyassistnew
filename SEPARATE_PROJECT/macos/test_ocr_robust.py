import cv2
import numpy as np
from PIL import Image
import pytesseract
from pytesseract import Output

# Create a dummy image (e.g. a blue button with white text "Post")
img = np.zeros((200, 400, 3), dtype=np.uint8)
img[:] = (255, 255, 255) # White background
cv2.rectangle(img, (50, 50), (150, 100), (200, 100, 50), -1) # Blue button
cv2.putText(img, "Post", (65, 85), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

# Robust OCR Logic
def extract_text(screen_bgr):
    scaled = cv2.resize(screen_bgr, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    rgb = scaled[:, :, ::-1]
    
    gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    inverted = cv2.bitwise_not(thresh)
    
    passes = [
        (Image.fromarray(rgb), "Normal"),
        (Image.fromarray(thresh), "Thresh"),
        (Image.fromarray(inverted), "Inverted"),
    ]
    
    for pil_img, name in passes:
        data = pytesseract.image_to_data(pil_img, output_type=Output.DICT, config='--psm 11')
        for i in range(len(data["text"])):
            conf = int(data["conf"][i])
            text = str(data["text"][i]).strip()
            if conf >= 30 and text:
                print(f"[{name}] Found '{text}' at conf={conf}")

extract_text(img)
