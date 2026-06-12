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
from bol.modules.m3_visual.semantic_dict import get_semantic_intent

# Windows compatibility for Tesseract binary
if sys.platform.startswith('win'):
    # Look for bundled tesseract in the project root first
    project_root = Path(__file__).parent.parent.parent.parent
    bundled_tesseract = project_root / "tesseract" / "tesseract.exe"
    
    if bundled_tesseract.exists():
        pytesseract.pytesseract.tesseract_cmd = str(bundled_tesseract)
        # Critical: Tell Tesseract where the language data is!
        tessdata_dir = project_root / "tesseract" / "tessdata"
        if tessdata_dir.exists():
            os.environ["TESSDATA_PREFIX"] = str(tessdata_dir)
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
            # Use Adaptive Thresholding with a larger block size (31 instead of 11) to handle buttons better
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2)
            
            # 2a. Thresh (fixes low contrast)
            pil_thresh = Image.fromarray(thresh)
            data_thresh = pytesseract.image_to_data(pil_thresh, output_type=Output.DICT, config='--psm 11')
            
            # 2b. Inverted Thresh (fixes white text on colored backgrounds)
            inverted = cv2.bitwise_not(thresh)
            pil_inverted = Image.fromarray(inverted)
            data_inverted = pytesseract.image_to_data(pil_inverted, output_type=Output.DICT, config='--psm 11')
            
            # 3. Global Otsu passes (great for solid buttons like Facebook)
            _, otsu_thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            pil_otsu = Image.fromarray(otsu_thresh)
            data_otsu = pytesseract.image_to_data(pil_otsu, output_type=Output.DICT, config='--psm 11')
            
            otsu_inverted = cv2.bitwise_not(otsu_thresh)
            pil_otsu_inverted = Image.fromarray(otsu_inverted)
            data_otsu_inverted = pytesseract.image_to_data(pil_otsu_inverted, output_type=Output.DICT, config='--psm 11')
            
            # 4. Direct Inverted Grayscale
            gray_inverted = cv2.bitwise_not(gray)
            pil_gray_inverted = Image.fromarray(gray_inverted)
            data_gray_inverted = pytesseract.image_to_data(pil_gray_inverted, output_type=Output.DICT, config='--psm 11')
            
        except pytesseract.TesseractNotFoundError:
            logger.error("Tesseract OCR binary not found on this system!")
            return OCRResult(words=[], full_text="")
        except Exception as e:
            logger.error(f"Tesseract Engine Error: {e}")
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
        process_data(data_otsu)
        process_data(data_otsu_inverted)
        process_data(data_gray_inverted)
        
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

        # Sort spatially (reading order: top-to-bottom, then left-to-right)
        # Using a line height bucket of 15px to align words on the same line
        deduped_words.sort(key=lambda w: (w.bounding_box.y // 15, w.bounding_box.x))

        screen_h, screen_w = screen_bgr.shape[:2]
        button_rects = self._find_button_contours(screen_bgr)
        
        colored_words_list = []
        full_text_strings = []
        for w in deduped_words:
            # Color
            color = self._get_bg_color_name(screen_bgr, w.bounding_box)
            
            # Zone
            cx = w.bounding_box.x + w.bounding_box.width // 2
            cy = w.bounding_box.y + w.bounding_box.height // 2
            zone = self._get_screen_zone(cx, cy, screen_w, screen_h)
            
            # Semantic Intent
            intent = get_semantic_intent(w.text.strip())
            
            # Is Button?
            is_button = False
            for (bx, by, bw, bh) in button_rects:
                if bx <= cx <= bx + bw and by <= cy <= by + bh:
                    is_button = True
                    break
                    
            tags = []
            if color != "unknown": tags.append(f"[bg:{color}]")
            tags.append(f"[zone:{zone}]")
            if is_button: tags.append("[type:button]")
            if intent: tags.append(f"[intent:{intent}]")
            
            tag_str = " ".join(tags)
            new_text = f"{w.text} {tag_str}" if tag_str else w.text
                
            colored_words_list.append(OCRWord(text=new_text, bounding_box=w.bounding_box, confidence=w.confidence))
            full_text_strings.append(new_text)

        return OCRResult(
            words=colored_words_list,
            full_text=" ".join(full_text_strings),
        )

    def _get_screen_zone(self, x: int, y: int, screen_w: int, screen_h: int) -> str:
        if y < screen_h * 0.15: return "top-nav"
        if y > screen_h * 0.85: return "footer"
        if x < screen_w * 0.20: return "sidebar"
        return "main-content"

    def _find_button_contours(self, screen_bgr: np.ndarray) -> list[tuple[int, int, int, int]]:
        import cv2
        gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        button_rects = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if h > 0:
                aspect_ratio = w / h
                if 1.5 < aspect_ratio < 8 and 20 < h < 100 and w > 40:
                    button_rects.append((x, y, w, h))
        return button_rects

    def _get_bg_color_name(self, screen_bgr: np.ndarray, bbox: BoundingBox) -> str:
        import cv2
        import numpy as np
        
        # Expand bbox by 5 pixels
        pad = 5
        h, w = screen_bgr.shape[:2]
        x1 = max(0, bbox.x - pad)
        y1 = max(0, bbox.y - pad)
        x2 = min(w, bbox.x + bbox.width + pad)
        y2 = min(h, bbox.y + bbox.height + pad)
        
        # Extract the perimeter mask
        mask = np.ones((y2-y1, x2-x1), dtype=np.uint8)
        inner_x1 = max(0, bbox.x - x1)
        inner_y1 = max(0, bbox.y - y1)
        inner_x2 = min(x2-x1, bbox.x + bbox.width - x1)
        inner_y2 = min(y2-y1, bbox.y + bbox.height - y1)
        
        if inner_y2 > inner_y1 and inner_x2 > inner_x1:
            mask[inner_y1:inner_y2, inner_x1:inner_x2] = 0
            
        roi = screen_bgr[y1:y2, x1:x2]
        perimeter_pixels = roi[mask == 1]
        
        if len(perimeter_pixels) == 0:
            return "unknown"
            
        median_bgr = np.median(perimeter_pixels, axis=0)
        b, g, r = median_bgr
        
        # Simple color mapping using Euclidean distance
        colors = {
            "black": (0, 0, 0),
            "white": (255, 255, 255),
            "red": (0, 0, 255),
            "green": (0, 255, 0),
            "blue": (255, 0, 0),
            "yellow": (0, 255, 255),
            "cyan": (255, 255, 0),
            "magenta": (255, 0, 255),
            "gray": (128, 128, 128)
        }
        
        min_dist = float('inf')
        best_color = "unknown"
        for name, (cb, cg, cr) in colors.items():
            dist = (b - cb)**2 + (g - cg)**2 + (r - cr)**2
            if dist < min_dist:
                min_dist = dist
                best_color = name
                
        return best_color

    def _expand_to_button(self, screen_bgr: np.ndarray, text_bbox: BoundingBox) -> tuple[BoundingBox, bool]:
        import cv2
        gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
        
        # Edge detection to find UI element boundaries (tuned for macOS low contrast)
        edges = cv2.Canny(gray, 15, 50)
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)
        
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        best_button_bbox = text_bbox
        min_button_area = float('inf')
        is_button = False
        
        tx, ty, tw, th = text_bbox.x, text_bbox.y, text_bbox.width, text_bbox.height
        text_cx, text_cy = tx + tw / 2, ty + th / 2
        
        screen_area = screen_bgr.shape[0] * screen_bgr.shape[1]
        
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            
            # Check if this contour encloses the text's center
            if x <= text_cx <= x + w and y <= text_cy <= y + h:
                # Relaxed constraints to detect tightly padded modern buttons
                if w >= tw * 1.05 or h >= th * 1.10:
                    area = w * h
                    # It shouldn't be massive (e.g. not the whole page container)
                    if area < screen_area * 0.25:
                        if area < min_button_area:
                            min_button_area = area
                            is_button = True
                            best_button_bbox = BoundingBox(
                                x=x, y=y, width=w, height=h, confidence=text_bbox.confidence
                            )
                            
        return best_button_bbox, is_button

    def find_text_on_screen(
        self, screen_bgr: np.ndarray, target: str,
        below: str | None = None,
        above: str | None = None,
        right_of: str | None = None,
        left_of: str | None = None,
    ) -> list[BoundingBox]:
        """
        Find all occurrences of target text on screen.

        For multi-word targets, finds consecutive matching words
        and merges their bounding boxes.
        Automatically expands the bounding box to the enclosing button.
        Supports modifiers: B- (Button only), T- (Text only), Bup- (Bottom up), Tbo- (Top down).

        Parameters
        ----------
        screen_bgr : numpy.ndarray
            BGR image array.
        target : str
            Text to search for (case-insensitive). Modifiers like B-Post can be used.

        Returns
        -------
        list[BoundingBox]
            Bounding boxes of the buttons containing the target text.
        """
        
        is_button_only = False
        is_text_only = False
        sort_bottom_up = False
        sort_top_down = False
        is_exact_match = False
        
        original_target = target
        parts = target.split('-')
        while len(parts) > 1:
            prefix = parts[0].upper()
            if prefix == 'B':
                is_button_only = True
                parts.pop(0)
            elif prefix == 'T':
                is_text_only = True
                parts.pop(0)
            elif prefix == 'BUP':
                sort_bottom_up = True
                parts.pop(0)
            elif prefix == 'TBO':
                sort_top_down = True
                parts.pop(0)
            elif prefix == 'E':
                is_exact_match = True
                parts.pop(0)
            else:
                break
                
        search_target = '-'.join(parts)
        if not search_target:
            search_target = original_target
            
        ocr_result = self.extract_text(screen_bgr)
        
        import re
        tags_in_target = [t.lower() for t in re.findall(r'\[.*?\]', search_target)]
        clean_target = re.sub(r'\[.*?\]', '', search_target).strip().lower()
        
        results: list[BoundingBox] = []

        # Group words to handle multi-word targets that Tesseract separated
        grouped_words = self.group_words_into_blocks(ocr_result.words, screen_bgr)
        
        # Determine target intent for fallback matching
        from bol.modules.m3_visual.semantic_dict import get_semantic_intent
        target_intent = get_semantic_intent(clean_target) if clean_target else None

        for block in grouped_words:
            block_clean = re.sub(r'\[.*?\]', '', block.text).strip().lower()
            
            # Primary match: Exact text or Substring
            is_match = False
            if clean_target:
                if is_exact_match:
                    if clean_target == block_clean:
                        is_match = True
                else:
                    if clean_target in block_clean:
                        is_match = True
            else:
                is_match = True
                
            # Secondary match: Semantic intent fallback
            if not is_match and target_intent:
                if f"[intent:{target_intent.lower()}]" in block.text.lower():
                    is_match = True
                    
            if is_match:
                if all(tag in block.text.lower() for tag in tags_in_target):
                    results.append(block.bounding_box)

        # Fallback: if block matching failed, text might have been split across blocks. Search raw words.
        if not results and clean_target:
            target_words = clean_target.split()
            if target_words:
                words = ocr_result.words
                for i in range(len(words) - len(target_words) + 1):
                    sequence = words[i : i + len(target_words)]
                    seq_text = " ".join(w.text.lower() for w in sequence)
                    if seq_text == clean_target:
                        merged_box = self._merge_bounding_boxes([w.bounding_box for w in sequence])
                        results.append(merged_box)

        # Expand text bounds to actual button bounds and apply filters
        filtered_results = []
        for res in results:
            expanded_bbox, is_btn = self._expand_to_button(screen_bgr, res)
            
            if is_button_only and not is_btn:
                continue
            if is_text_only and is_btn:
                continue
                
            filtered_results.append(expanded_bbox)
            
        if sort_bottom_up:
            filtered_results.sort(key=lambda b: b.y, reverse=True)
        elif sort_top_down:
            filtered_results.sort(key=lambda b: b.y, reverse=False)

        # Apply spatial constraints if provided
        final_results = filtered_results
        if below or above or right_of or left_of:
            anchor_results = []
            if below: anchor_results = self.find_text_on_screen(screen_bgr, below)
            elif above: anchor_results = self.find_text_on_screen(screen_bgr, above)
            elif right_of: anchor_results = self.find_text_on_screen(screen_bgr, right_of)
            elif left_of: anchor_results = self.find_text_on_screen(screen_bgr, left_of)
            
            if anchor_results:
                anchor = anchor_results[0]  # Use the first/best match for the anchor
                spatially_filtered = []
                for res in filtered_results:
                    if below and res.y > anchor.y + anchor.height * 0.5:
                        spatially_filtered.append(res)
                    elif above and res.y + res.height < anchor.y + anchor.height * 0.5:
                        spatially_filtered.append(res)
                    elif right_of and res.x > anchor.x + anchor.width * 0.5:
                        spatially_filtered.append(res)
                    elif left_of and res.x + res.width < anchor.x + anchor.width * 0.5:
                        spatially_filtered.append(res)
                final_results = spatially_filtered
            else:
                # SAFETY: anchor was specified but not found — UI is not in the expected state.
                # Return EMPTY so the caller retries. Never click randomly when anchor is missing.
                logger.warning(f"Spatial anchor not found on screen. Returning empty to force retry — will NOT click blindly.")
                final_results = []


        logger.debug("Found %d occurrences of '%s' (filtered & expanded)", len(final_results), original_target)
        return final_results

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

    def group_words_into_blocks(self, words: list[OCRWord], screen_bgr: np.ndarray | None = None) -> list[OCRWord]:
        """
        Group individual OCRWords spatially into cohesive lines and text blocks.
        Optionally re-applies tags (color, zone, button status, intent) to the merged blocks.
        """
        if not words:
            return []

        import re
        from bol.modules.m3_visual.semantic_dict import get_semantic_intent

        # 1. Clean words (strip existing tags to get clean texts)
        clean_words = []
        for w in words:
            clean_txt = re.sub(r'\s*\[.*?\]', '', w.text).strip()
            if clean_txt:
                clean_words.append(
                    OCRWord(text=clean_txt, bounding_box=w.bounding_box, confidence=w.confidence)
                )

        if not clean_words:
            return []

        # 2. Cluster words into horizontal lines
        # A line contains words whose y-centers are close (within 12 pixels)
        lines: list[list[OCRWord]] = []
        # Sort words primarily by y, then by x
        sorted_words = sorted(clean_words, key=lambda w: (w.bounding_box.y, w.bounding_box.x))

        for w in sorted_words:
            added = False
            cy = w.bounding_box.y + w.bounding_box.height / 2
            for line in lines:
                # Calculate average y-center of this line
                line_cy = sum(lw.bounding_box.y + lw.bounding_box.height / 2 for lw in line) / len(line)
                if abs(cy - line_cy) <= 12:
                    line.append(w)
                    added = True
                    break
            if not added:
                lines.append([w])

        # 3. Within each line, group words that are close horizontally (gap <= 25 pixels)
        grouped_blocks: list[OCRWord] = []
        for line in lines:
            line_sorted = sorted(line, key=lambda w: w.bounding_box.x)
            current_group: list[OCRWord] = []

            for w in line_sorted:
                if not current_group:
                    current_group.append(w)
                else:
                    prev_w = current_group[-1]
                    gap = w.bounding_box.x - (prev_w.bounding_box.x + prev_w.bounding_box.width)
                    if gap <= 25:
                        current_group.append(w)
                    else:
                        grouped_blocks.append(self._merge_words(current_group))
                        current_group = [w]
            if current_group:
                grouped_blocks.append(self._merge_words(current_group))

        # Sort all blocks top-to-bottom, left-to-right
        grouped_blocks.sort(key=lambda w: (w.bounding_box.y // 15, w.bounding_box.x))

        # 4. Optionally apply tags to the grouped blocks
        if screen_bgr is not None:
            screen_h, screen_w = screen_bgr.shape[:2]
            button_rects = self._find_button_contours(screen_bgr)
            tagged_blocks = []
            for b in grouped_blocks:
                color = self._get_bg_color_name(screen_bgr, b.bounding_box)
                cx = b.bounding_box.x + b.bounding_box.width // 2
                cy = b.bounding_box.y + b.bounding_box.height // 2
                zone = self._get_screen_zone(cx, cy, screen_w, screen_h)
                intent = get_semantic_intent(b.text.strip())

                is_button = False
                for (bx, by, bw, bh) in button_rects:
                    if bx <= cx <= bx + bw and by <= cy <= by + bh:
                        is_button = True
                        break

                tags = []
                if color != "unknown": tags.append(f"[bg:{color}]")
                tags.append(f"[zone:{zone}]")
                if is_button: tags.append("[type:button]")
                if intent: tags.append(f"[intent:{intent}]")

                tag_str = " ".join(tags)
                new_text = f"{b.text} {tag_str}" if tag_str else b.text
                tagged_blocks.append(OCRWord(text=new_text, bounding_box=b.bounding_box, confidence=b.confidence))
            return tagged_blocks

        return grouped_blocks

    def _merge_words(self, words: list[OCRWord]) -> OCRWord:
        """Helper to merge multiple OCRWords into a single OCRWord."""
        if len(words) == 1:
            return words[0]

        merged_box = self._merge_bounding_boxes([w.bounding_box for w in words])
        joined_text = " ".join(w.text for w in words)
        avg_conf = int(sum(w.confidence for w in words) / len(words))

        return OCRWord(
            text=joined_text,
            bounding_box=merged_box,
            confidence=avg_conf
        )

