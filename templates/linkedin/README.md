# LinkedIn Template Assets

This directory contains OpenCV reference template images for LinkedIn UI elements.

## Required Templates

To calibrate the system, capture screenshots of these LinkedIn UI elements:

1. **`start_post_button.png`** — The "Start a post" button/text area on the LinkedIn feed
2. **`post_submit_button.png`** — The "Post" button in the post composition dialog  
3. **`notification_badge.png`** — The red notification badge icon
4. **`post_dialog.png`** — The post composition dialog frame
5. **`cancel_button.png`** — The cancel/discard button in the post dialog

## Capture Instructions

1. Open Chrome with your LinkedIn profile
2. Navigate to `linkedin.com/feed`
3. Use macOS Screenshot (Cmd+Shift+4) to capture each element
4. Crop tightly around the UI element (minimal background)
5. Save as PNG in this directory with the names above
6. Ensure captures are at your display's native resolution

## Important Notes

- Templates should be captured at the **same display scale** as the automation target
- Retina displays: mss captures at physical pixel resolution
- Re-capture templates if LinkedIn updates their UI
- Keep templates clean — no overlapping elements or tooltips visible
