"""
OCR text extraction engine using pytesseract.

Extracts text and bounding boxes from screen captures,
enabling text-based UI element location.
"""

from __future__ import annotations

import numpy as np
import pytesseract
from PIL import Image
from pytesseract import Output
import sys
import os
from pathlib import Path

# Windows compatibility for Tesseract binary
if sys.platform.startswith('win'):
    # Look for bundled tesseract in the project root first
    project_root = Path(__file__).parent.parent.parent.parent
    bundled_tesseract = project_root / "tesseract" / "tesseract.exe"
    
    if bundled_tesseract.exists():
        pytesseract.pytesseract.tesseract_cmd = str(bundled_tesseract)
    else:
        # Fallback to common installation path
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

from bol.schemas.visual import BoundingBox, OCRResult, OCRWord
from bol.utils.logging import get_logger

logger = get_logger(__name__)


class OCREngine:
    """
    Text extraction from screen captures using Tesseract OCR.

    Provides word-level bounding boxes with confidence scores
    and multi-word text search capabilities.
    """

    def __init__(
        self,
        tesseract_cmd: str | None = None,
        confidence_threshold: int = 60,
    ) -> None:
        """
        Initialize the OCR engine.

        Parameters
        ----------
        tesseract_cmd : str | None
            Path to the Tesseract binary. If None, uses system default.
        confidence_threshold : int
            Minimum confidence score (0-100) for accepting OCR results.
        """
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self._confidence_threshold = confidence_threshold

    def extract_text(self, screen_bgr: np.ndarray) -> OCRResult:
        import cv2
        # Scale by 2x for better OCR on small web fonts
        scaled = cv2.resize(screen_bgr, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        try:
            # 1. Normal pass
            rgb = scaled[:, :, ::-1]
            pil_image = Image.fromarray(rgb)
            data_normal = pytesseract.image_to_data(pil_image, output_type=Output.DICT, config='--psm 11')
            
            # 2. Threshold passes
            gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 2a. Thresh (fixes low contrast)
            pil_thresh = Image.fromarray(thresh)
            data_thresh = pytesseract.image_to_data(pil_thresh, output_type=Output.DICT, config='--psm 11')
            
            # 2b. Inverted Thresh (fixes white text on colored backgrounds)
            inverted = cv2.bitwise_not(thresh)
            pil_inverted = Image.fromarray(inverted)
            data_inverted = pytesseract.image_to_data(pil_inverted, output_type=Output.DICT, config='--psm 11')
        except pytesseract.TesseractNotFoundError:
            logger.error("Tesseract OCR binary not found on this system!")
            return OCRResult(words=[], full_text="")

        words: list[OCRWord] = []
        
        def process_data(data):
            n_boxes = len(data["text"])
            for i in range(n_boxes):
                conf = int(data["conf"][i])
                text = str(data["text"][i]).strip()

                if conf >= self._confidence_threshold and text:
                    # Divide by 2 to map back to original screen coordinates
                    bbox = BoundingBox(
                        x=int(data["left"][i]) // 2,
                        y=int(data["top"][i]) // 2,
                        width=max(int(data["width"][i]) // 2, 1),
                        height=max(int(data["height"][i]) // 2, 1),
                        confidence=conf / 100.0,
                    )
                    words.append(OCRWord(text=text, bounding_box=bbox, confidence=conf))
                    
        process_data(data_normal)
        process_data(data_thresh)
        process_data(data_inverted)
        
        # Deduplicate identical words found in same physical location
        deduped_words = []
        for w in words:
            is_dup = False
            for dw in deduped_words:
                if w.text.lower() == dw.text.lower():
                    # Check if centers are within 10 pixels
                    cx1 = w.bounding_box.x + w.bounding_box.width/2
                    cy1 = w.bounding_box.y + w.bounding_box.height/2
                    cx2 = dw.bounding_box.x + dw.bounding_box.width/2
                    cy2 = dw.bounding_box.y + dw.bounding_box.height/2
                    if abs(cx1-cx2) < 10 and abs(cy1-cy2) < 10:
                        is_dup = True
                        break
            if not is_dup:
                deduped_words.append(w)

        return OCRResult(
            words=deduped_words,
            full_text=" ".join([w.text for w in deduped_words]),
        )

    def find_text_on_screen(
        self, screen_bgr: np.ndarray, target: str
    ) -> list[BoundingBox]:
        """
        Find all occurrences of target text on screen.

        For multi-word targets, finds consecutive matching words
        and merges their bounding boxes.

        Parameters
        ----------
        screen_bgr : numpy.ndarray
            BGR image array.
        target : str
            Text to search for (case-insensitive).

        Returns
        -------
        list[BoundingBox]
            Bounding boxes containing the target text.
        """
        ocr_result = self.extract_text(screen_bgr)
        target_words = target.lower().split()
        results: list[BoundingBox] = []

        if len(target_words) == 1:
            # Single-word search
            for word in ocr_result.words:
                if target_words[0] in word.text.lower():
                    results.append(word.bounding_box)
        else:
            # Multi-word: look for consecutive matching words
            for i in range(len(ocr_result.words) - len(target_words) + 1):
                match = True
                for j, tw in enumerate(target_words):
                    if tw not in ocr_result.words[i + j].text.lower():
                        match = False
                        break
                if match:
                    # Merge bounding boxes of consecutive words
                    merged = self._merge_bounding_boxes(
                        [ocr_result.words[i + j].bounding_box for j in range(len(target_words))]
                    )
                    results.append(merged)

        logger.debug("Found %d occurrences of '%s'", len(results), target)
        return results

    @staticmethod
    def _merge_bounding_boxes(boxes: list[BoundingBox]) -> BoundingBox:
        """Merge multiple bounding boxes into one encompassing box."""
        x_min = min(b.x for b in boxes)
        y_min = min(b.y for b in boxes)
        x_max = max(b.x + b.width for b in boxes)
        y_max = max(b.y + b.height for b in boxes)
        avg_conf = sum(b.confidence for b in boxes) / len(boxes)

        return BoundingBox(
            x=x_min,
            y=y_min,
            width=x_max - x_min,
            height=y_max - y_min,
            confidence=avg_conf,
        )
