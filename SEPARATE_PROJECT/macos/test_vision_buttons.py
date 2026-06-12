"""
Quick test: takes a screenshot, runs all VISIONBUTTONS templates against it,
draws green boxes where matches are found, and saves the result.

Run with:  python3 test_vision_buttons.py
Then open: vision_test_result.png
"""

import cv2
import numpy as np
import mss
import mss.tools
from pathlib import Path
import sys

VISIONBUTTONS_DIR = Path(__file__).parent / "VISIONBUTTONS"
OUT_PATH = Path(__file__).parent / "vision_test_result.png"

PLATFORM_DIRS = {
    "facebook":  VISIONBUTTONS_DIR / "facebookbuttons",
    "instagram": VISIONBUTTONS_DIR / "instagrambuttons",
    "linkedin":  VISIONBUTTONS_DIR / "linkedinbuttons",
    "x":         VISIONBUTTONS_DIR / "xbuttons",
    "whatsapp":  VISIONBUTTONS_DIR / "whatsappbuttons",
}

MIN_CONFIDENCE = 0.62
# Retina macs save screenshots at 2x pixel density.
# The live mss capture is at 1x logical resolution.
# So we must try 0.5 scale (halve the template) as the primary scale.
SCALES = [0.5, 0.55, 0.45, 0.6, 0.4, 1.0, 0.85, 0.75]

def load_templates():
    templates = {}
    for platform, folder in PLATFORM_DIRS.items():
        if not folder.exists():
            continue
        for img_path in sorted(folder.glob("*.png")):
            tmpl = cv2.imread(str(img_path))
            if tmpl is not None:
                templates[img_path.stem] = tmpl
    print(f"Loaded {len(templates)} templates")
    return templates

def find_template(screenshot_gray, tmpl_gray, threshold=MIN_CONFIDENCE):
    th, tw = tmpl_gray.shape[:2]
    best_conf = 0.0
    best_loc = None
    best_scale = 1.0

    for scale in SCALES:
        sw = max(1, int(tw * scale))
        sh = max(1, int(th * scale))
        if sh > screenshot_gray.shape[0] or sw > screenshot_gray.shape[1]:
            continue
        scaled = cv2.resize(tmpl_gray, (sw, sh))
        result = cv2.matchTemplate(screenshot_gray, scaled, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val > best_conf:
            best_conf = max_val
            best_loc = max_loc
            best_scale = scale

    if best_conf >= threshold and best_loc:
        mw = int(tw * best_scale)
        mh = int(th * best_scale)
        return best_loc, mw, mh, best_conf, best_scale
    return None, None, None, best_conf, best_scale


def autocrop_whitespace(gray):
    """Remove surrounding white border from a template."""
    # Invert so dark content = bright
    inv = cv2.bitwise_not(gray)
    coords = cv2.findNonZero(inv)
    if coords is None:
        return gray
    x, y, w, h = cv2.boundingRect(coords)
    pad = 4
    x = max(0, x - pad)
    y = max(0, y - pad)
    w = min(gray.shape[1] - x, w + pad * 2)
    h = min(gray.shape[0] - y, h + pad * 2)
    return gray[y:y+h, x:x+w]

def capture_screen():
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        shot = sct.grab(monitor)
        arr = np.frombuffer(shot.raw, dtype=np.uint8)
        arr = arr.reshape((shot.height, shot.width, 4))
        bgr = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        return bgr, gray

def main():
    # Filter by platform if given as arg
    filter_platform = sys.argv[1] if len(sys.argv) > 1 else None

    print("Capturing screen in 2 seconds... Switch to the website you want to test!")
    import time
    time.sleep(2)

    screenshot, screenshot_gray = capture_screen()
    overlay = screenshot.copy()
    print(f"Screenshot: {screenshot.shape[1]}x{screenshot.shape[0]}")

    templates = load_templates()

    # Pre-convert all templates to grayscale + autocrop whitespace
    templates_gray = {}
    for name, tmpl in templates.items():
        g = cv2.cvtColor(tmpl, cv2.COLOR_BGR2GRAY)
        # For nav items, autocrop to remove white borders
        if "_nav_" in name and not name.endswith("_nav_menu"):
            g = autocrop_whitespace(g)
        templates_gray[name] = g

    debug_dir = Path("vision_debug_crops")
    debug_dir.mkdir(exist_ok=True)

    matches_found = []
    not_found = []

    for name, tmpl_gray in templates_gray.items():
        # Skip full nav_menu
        if name.endswith("_nav_menu"):
            continue
        # Filter by platform if requested
        if filter_platform and not name.startswith(filter_platform):
            continue

        loc, mw, mh, conf, scale = find_template(screenshot_gray, tmpl_gray)
        if loc:
            x, y = loc
            cx, cy = x + mw // 2, y + mh // 2
            # Draw green rectangle on colour overlay
            cv2.rectangle(overlay, (x, y), (x + mw, y + mh), (0, 220, 0), 2)
            label = f"{name} ({conf:.2f})"
            font = cv2.FONT_HERSHEY_SIMPLEX
            (lw, lh), _ = cv2.getTextSize(label, font, 0.4, 1)
            cv2.rectangle(overlay, (x, y - lh - 4), (x + lw + 4, y), (0, 220, 0), -1)
            cv2.putText(overlay, label, (x + 2, y - 2), font, 0.4, (0, 0, 0), 1)
            cv2.circle(overlay, (cx, cy), 5, (0, 0, 255), -1)
            matches_found.append((name, conf, cx, cy))
            print(f"  ✅ {name:50s}  conf={conf:.3f}  scale={scale:.2f}  center=({cx},{cy})")
        else:
            not_found.append((name, conf))
            near = "  (near miss)" if conf > 0.50 else ""
            print(f"  ❌ {name:50s}  best={conf:.3f}  scale={scale:.2f}{near}")
            # Save debug crop of where the best match was found
            if conf > 0.45:
                # Re-run to get location of best (even below threshold)
                th2, tw2 = tmpl_gray.shape[:2]
                for sc in SCALES:
                    sw2 = max(1, int(tw2 * sc))
                    sh2 = max(1, int(th2 * sc))
                    if sh2 > screenshot_gray.shape[0] or sw2 > screenshot_gray.shape[1]:
                        continue
                    scaled2 = cv2.resize(tmpl_gray, (sw2, sh2))
                    result2 = cv2.matchTemplate(screenshot_gray, scaled2, cv2.TM_CCOEFF_NORMED)
                    _, mv, _, ml = cv2.minMaxLoc(result2)
                    if abs(mv - conf) < 0.005:
                        rx, ry = ml
                        crop = screenshot[max(0,ry-5):ry+sh2+5, max(0,rx-5):rx+sw2+5]
                        cv2.imwrite(str(debug_dir / f"{name}_found_at.png"), crop)
                        break

    cv2.imwrite(str(OUT_PATH), overlay)
    print(f"\n{'='*60}")
    print(f"FOUND:     {len(matches_found)}")
    print(f"NOT FOUND: {len(not_found)}")
    print(f"Result saved: {OUT_PATH}")
    print(f"Open it to see green boxes on matched buttons.")

if __name__ == "__main__":
    main()
