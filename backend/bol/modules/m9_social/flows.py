"""
Social Media Posting Flows — Step-by-step state machine definitions.

Each platform has an ordered list of Steps. Each Step says:
  - what state/page we are on
  - EXACTLY which button/text to look for
  - what action to take (click, type, upload)
  - what confirms this step is DONE before moving to the next

The agent MUST use these flows instead of ad-hoc LLM guessing.
Rule: "I am on step N of platform X → I look for THIS button, not any other."

Supported tasks:
  whatsapp_status        — post a WhatsApp status/story
  whatsapp_message       — send a WhatsApp DM
  instagram_post         — post a photo/video on Instagram feed
  instagram_reel         — post a Reel on Instagram
  facebook_post          — post a photo/text on Facebook feed
  linkedin_post          — post on LinkedIn feed
  x_post                 — post a tweet on X (Twitter)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ActionType(str, Enum):
    CLICK         = "click"         # click a button
    TYPE          = "type"          # type text into the active field
    UPLOAD        = "upload"        # open file picker and select a file
    OS_OPEN       = "os_open"       # click the OS file dialog "Open" button
    WAIT          = "wait"          # wait N seconds for page/animation
    NAVIGATE      = "navigate"      # open a URL in Chrome
    CONFIRM_DONE  = "confirm_done"  # final step — task is complete
    HOVER_AND_VERIFY = "hover_and_verify" # move over template, wait, OCR verify text, then click
    PRESS_ENTER   = "press_enter"   # press the return key


@dataclass
class Step:
    """One step in a posting workflow."""
    number: int
    description: str                     # human-readable intent
    action: ActionType
    # --- what to look for on screen ---
    template: Optional[str] = None       # VISIONBUTTONS template name (primary)
    text_fallback: Optional[str] = None  # OCR text to click if template misses
    url: Optional[str] = None            # for NAVIGATE action
    type_text_key: Optional[str] = None  # placeholder key e.g. "caption", "message"
    file_key: Optional[str] = None       # placeholder key for file path e.g. "media_path"
    wait_seconds: float = 0.0
    # --- confirmation ---
    confirm_template: Optional[str] = None   # template that must appear after this step
    confirm_text: Optional[str] = None       # OCR text that must appear after this step
    optional_if_no_key: Optional[str] = None # Skip this step if params[key] is empty (e.g. 'media_path')
    skip_if_key: Optional[str] = None        # Skip this step if params[key] is PRESENT (e.g. 'media_path')
    bypass_swarm: bool = False               # Skip Swarm Council safety checks (e.g., if button is in Dock zone)
    # --- precise clicking & spatial context ---
    offset_x: int = 0                        # Click offset X from the center of the match
    offset_y: int = 0                        # Click offset Y from the center of the match
    spatial_anchor_below: Optional[str] = None    # Find target ONLY below this text
    spatial_anchor_above: Optional[str] = None    # Find target ONLY above this text
    spatial_anchor_right_of: Optional[str] = None # Find target ONLY right of this text
    spatial_anchor_left_of: Optional[str] = None  # Find target ONLY left of this text
    # --- hover and verify ---
    hover_template: Optional[str] = None     # Base template to search for
    hover_verify_text: Optional[str] = None  # Text that must appear on hover
    notes: str = ""


@dataclass
class SocialFlow:
    """Complete posting workflow for one task on one platform."""
    task_id: str          # e.g. "whatsapp_status"
    platform: str         # whatsapp | instagram | facebook | linkedin | x
    url: str              # starting URL
    description: str
    steps: list[Step]


# ─────────────────────────────────────────────────────────────────────────────
# WHATSAPP STATUS (Story)
# ─────────────────────────────────────────────────────────────────────────────
WHATSAPP_STATUS = SocialFlow(
    task_id="whatsapp_status",
    platform="whatsapp",
    url="https://web.whatsapp.com",
    description="Post a status (story) on WhatsApp Web",
    steps=[
        Step(
            number=1,
            description="Open WhatsApp Web",
            action=ActionType.NAVIGATE,
            url="https://web.whatsapp.com",
            wait_seconds=4.0,
            notes="Wait for QR code or chat list to load."
        ),
        Step(
            number=2,
            description="Click on the Status tab in the left sidebar",
            action=ActionType.CLICK,
            template="whatsapp_story_icon",
            text_fallback="Status",
            wait_seconds=1.5,
            confirm_text="Status",
            notes="The status/story ring icon in the left panel."
        ),
        Step(
            number=3,
            description="Click the + (add new status) button",
            action=ActionType.CLICK,
            template="whatsapp_new_status_icon",
            text_fallback=None,
            wait_seconds=1.5,
            notes="The circular + button next to 'My Status'. Opens content picker."
        ),
        Step(
            number=4,
            description="Click 'Photos & Video' to open file picker (if media)",
            action=ActionType.CLICK,
            template=None,
            text_fallback="Photos",
            optional_if_no_key="media_path",
            wait_seconds=1.0,
            notes="Opens the OS file picker dialog."
        ),
        Step(
            number=5,
            description="OS file picker is open — click Open to confirm selection (if media)",
            action=ActionType.OS_OPEN,
            template="whatsapp_open_button",
            text_fallback="Open",
            wait_seconds=2.0,
            file_key="media_path",
            optional_if_no_key="media_path",
            notes="The blue Open button in the macOS file dialog. File must already be selected."
        ),
        Step(
            number=6,
            description="Click 'Text' option (if no media)",
            action=ActionType.CLICK,
            template="whatsapp_text_status_icon",
            text_fallback="Text",
            skip_if_key="media_path",
            wait_seconds=1.0,
            notes="Click the Text pencil icon when only a caption is provided."
        ),
        Step(
            number=7,
            description="Type the text status (if no media)",
            action=ActionType.TYPE,
            text_fallback="Type a status",
            type_text_key="caption",
            skip_if_key="media_path",
            wait_seconds=0.5,
            notes="Types the text into the status text area."
        ),
        Step(
            number=8,
            description="Type caption for image/video (if media)",
            action=ActionType.TYPE,
            text_fallback="Add a caption",
            type_text_key="caption",
            optional_if_no_key="media_path",
            wait_seconds=0.5,
            notes="Types the text into the media caption box."
        ),
        Step(
            number=9,
            description="Press Enter to post the status",
            action=ActionType.PRESS_ENTER,
            template=None,
            text_fallback=None,
            wait_seconds=2.0,
            confirm_text="My Status",
            notes="Presses OS Enter key instead of clicking."
        ),
        Step(
            number=10,
            description="Status posted successfully",
            action=ActionType.CONFIRM_DONE,
            notes="Task complete. WhatsApp status has been posted."
        ),
    ]
)


# ─────────────────────────────────────────────────────────────────────────────
# WHATSAPP MESSAGE (DM)
# ─────────────────────────────────────────────────────────────────────────────
WHATSAPP_MESSAGE = SocialFlow(
    task_id="whatsapp_message",
    platform="whatsapp",
    url="https://web.whatsapp.com",
    description="Send a WhatsApp message to a contact",
    steps=[
        Step(number=1, description="Open WhatsApp Web",
             action=ActionType.NAVIGATE, url="https://web.whatsapp.com", wait_seconds=4.0),
        Step(number=2, description="Find and click the contact in the chat list",
             action=ActionType.CLICK, text_fallback="contact_name",  # replaced at runtime
             wait_seconds=1.5, notes="Use OCR to find the contact name in the left panel."),
        Step(number=3, description="Click the message input box and type the message",
             action=ActionType.TYPE, type_text_key="message", wait_seconds=0.5,
             notes="Click inside the message text box first, then type."),
        Step(number=4, description="Click the send button",
             action=ActionType.CLICK, template="whatsapp_send_icon", text_fallback="Send",
             wait_seconds=1.0, notes="Green send arrow on the right of the input bar."),
        Step(number=7, description="Message sent successfully", action=ActionType.CONFIRM_DONE),
    ]
)


# ─────────────────────────────────────────────────────────────────────────────
# INSTAGRAM POST (Feed photo/video)
# ─────────────────────────────────────────────────────────────────────────────
# CRITICAL STEP MAPPING — the agent must follow this EXACTLY:
# Step 3: shows post type picker  → click instagram_post_button (not Share, not Next)
# Step 4: shows file picker        → click instagram_select_from_computer_button
# Step 5: OS Open dialog           → click instagram_open_button
# Step 6: shows crop/ratio screen  → click instagram_next_button  ← NOT Post/Share
# Step 7: shows filters screen     → click instagram_next_button  ← NOT Post/Share
# Step 8: shows caption screen     → type caption, then click instagram_share_button ← FINAL
INSTAGRAM_POST = SocialFlow(
    task_id="instagram_post",
    platform="instagram",
    url="https://www.instagram.com",
    description="Post a photo or video to Instagram feed",
    steps=[
        Step(number=1, description="Open Instagram",
             action=ActionType.NAVIGATE, url="https://www.instagram.com", wait_seconds=4.0),
        Step(number=2,
             description="Click the + button in the sidebar directly",
             action=ActionType.CLICK,
             template="instagram_new_post_icon",
             text_fallback="Create",
             wait_seconds=1.5,
             confirm_text="Post",
             notes="Finds and directly clicks the + icon in the left sidebar."),
        Step(number=3,
             description="Click 'Post' from the type picker (NOT the final Post button)",
             action=ActionType.CLICK,
             template="instagram_post_button",
             wait_seconds=1.5,
             notes="Post type selector row — selects Feed Post, opens media picker."),
        Step(number=4,
             description="Click 'Select from computer' to open file picker",
             action=ActionType.CLICK,
             template="instagram_select_from_computer_button",
             text_fallback="Select from computer",
             wait_seconds=1.5,
             notes="Opens the OS file dialog."),
        Step(number=5,
             description="OS file picker is open — click Open",
             action=ActionType.OS_OPEN,
             template="instagram_open_button",
             text_fallback="Open",
             file_key="media_path",
             wait_seconds=2.5,
             notes="Blue Open button in macOS file dialog."),
        Step(number=6,
             description="Crop/ratio screen — click Next to proceed (NOT Share)",
             action=ActionType.CLICK,
             template="instagram_next_button",
             text_fallback="Next",
             wait_seconds=1.5,
             confirm_template="instagram_next_button",
             notes="STEP 6: This is the crop screen. Next button appears top-right. "
                   "DO NOT click Share here — Share only appears in step 8."),
        Step(number=7,
             description="Filters screen — click Next again (NOT Share)",
             action=ActionType.CLICK,
             template="instagram_next_button",
             text_fallback="Next",
             wait_seconds=1.5,
             confirm_template="instagram_share_button",
             notes="STEP 7: This is the filters screen. Click Next to reach caption. "
                   "Share button will appear AFTER this step."),
        Step(number=8,
             description="Caption screen — click above smile icon and type caption",
             action=ActionType.TYPE,
             template="instagram_smile_icon",
             offset_y=-80,
             type_text_key="caption",
             wait_seconds=0.5,
             notes="Finds the smile icon, clicks 80 pixels above it to focus the text area, and types."),
        Step(number=9,
             description="Click Share to publish the post",
             action=ActionType.CLICK,
             template="instagram_share_button",
             text_fallback="Share",
             wait_seconds=3.0,
             confirm_text="Your post has been shared",
             notes="FINAL STEP: Blue Share button top-right. Post goes live."),
        Step(number=10, description="Post published successfully", action=ActionType.CONFIRM_DONE),
    ]
)


# ─────────────────────────────────────────────────────────────────────────────
# INSTAGRAM REEL
# ─────────────────────────────────────────────────────────────────────────────
INSTAGRAM_REEL = SocialFlow(
    task_id="instagram_reel",
    platform="instagram",
    url="https://www.instagram.com",
    description="Post a Reel to Instagram",
    steps=[
        Step(number=1, description="Open Instagram",
             action=ActionType.NAVIGATE, url="https://www.instagram.com", wait_seconds=4.0),
        Step(number=2, description="Click + Create in nav",
             action=ActionType.CLICK, template="instagram_nav_create", text_fallback="Create",
             wait_seconds=1.5),
        Step(number=3, description="Click 'Reel' from the type picker",
             action=ActionType.CLICK, template="instagram_reel_icon", text_fallback="Reel",
             wait_seconds=1.5, notes="Selects Reel type, opens media picker."),
        Step(number=4, description="Click 'Select from computer'",
             action=ActionType.CLICK, template="instagram_select_from_computer_button",
             text_fallback="Select from computer", wait_seconds=1.5),
        Step(number=5, description="OS file picker — click Open",
             action=ActionType.OS_OPEN, template="instagram_open_button",
             text_fallback="Open", file_key="media_path", wait_seconds=3.0),
        Step(number=6, description="Trim/edit screen — click Next",
             action=ActionType.CLICK, template="instagram_next_button",
             text_fallback="Next", wait_seconds=2.0,
             notes="NOT Share — this is the trim/edit screen."),
        Step(number=7, description="Caption screen — type caption",
             action=ActionType.TYPE, type_text_key="caption", wait_seconds=0.5),
        Step(number=8, description="Click Share to publish Reel",
             action=ActionType.CLICK, template="instagram_share_button",
             text_fallback="Share", wait_seconds=4.0),
        Step(number=9, description="Reel published successfully", action=ActionType.CONFIRM_DONE),
    ]
)


# ─────────────────────────────────────────────────────────────────────────────
# FACEBOOK POST
# ─────────────────────────────────────────────────────────────────────────────
# CRITICAL STEP MAPPING:
# Step 3: click Photo/Video icon — opens file picker
# Step 4: OS file dialog → click Open (facebook_open_button)
# Step 5: preview screen → click Post (facebook_post_button) ← FINAL
# NOTE: facebook_next_button appears in a DIFFERENT sub-flow (albums).
#       For simple photo post, it goes directly: photo_icon → open → post.
# Facebook TEXT-ONLY post (no media)
# REAL FLOW observed on Facebook:
# 1. Open Facebook
# 2. Click "What's on your mind?"
# 3. Type the text
# 4. Click Next (Facebook shows audience selector / confirmation step)
# 5. Click Post (FINAL)
FACEBOOK_TEXT_POST = SocialFlow(
    task_id="facebook_text_post",
    platform="facebook",
    url="https://www.facebook.com",
    description="Post a text status on Facebook feed",
    steps=[
        Step(number=1, description="Open Facebook",
             action=ActionType.NAVIGATE, url="https://www.facebook.com", wait_seconds=4.0),
        Step(number=2,
             description="Click 'What's on your mind?' to open the post composer",
             action=ActionType.CLICK,
             text_fallback="What's on your mind",
             wait_seconds=1.5,
             notes="OCR finds 'What's on your mind' on the feed. Opens the composer modal."),
        Step(number=3,
             description="Wait for composer modal to fully open",
             action=ActionType.WAIT,
             wait_seconds=2.0,
             notes="The composer modal animates open. Wait for it to settle."),
        Step(number=4,
             description="Type the post text",
             action=ActionType.TYPE,
             type_text_key="caption",
             wait_seconds=0.5,
             notes="The composer text area should be auto-focused after the modal opens."),
        Step(number=5,
             description="Click Post to publish",
             action=ActionType.CLICK,
             text_fallback="B-Post",
             wait_seconds=3.0,
             notes="FINAL STEP: Pure OCR: finds 'Post' as a button shape. B- forces button-only match. No anchor or template needed."),
        Step(number=6, description="Post published successfully", action=ActionType.CONFIRM_DONE),
    ]
)


# Facebook POST (Text, Media, or both)
# 1. Open Facebook
# 2. Click "What's on your mind?"
# 3. Type caption
# 4. Click Add Photo/Video button (if media attached)
# 5. File picker → Open
# 6. Click Post (FINAL)
FACEBOOK_POST = SocialFlow(
    task_id="facebook_post",
    platform="facebook",
    url="https://www.facebook.com",
    description="Post text, photo or video on Facebook feed",
    steps=[
        Step(number=1, description="Open Facebook",
             action=ActionType.NAVIGATE, url="https://www.facebook.com", wait_seconds=4.0),
        Step(number=2,
             description="Click 'What's on your mind?' to open the post composer",
             action=ActionType.CLICK,
             text_fallback="What's on your mind",
             wait_seconds=1.5,
             notes="Opens the composer modal."),
        Step(number=3,
             description="Wait for composer modal to fully open",
             action=ActionType.WAIT,
             wait_seconds=2.0,
             notes="The composer modal animates open. Wait for it to fully settle before typing."),
        Step(number=4,
             description="Type caption text",
             action=ActionType.TYPE,
             type_text_key="caption",
             wait_seconds=0.5,
             notes="Text area is auto-focused after modal opens. Will skip if no text provided."),
        Step(number=5,
             description="Click the 'Add photos or videos' upload area",
             action=ActionType.CLICK,
             template="facebook_s6_add_photo_button",
             text_fallback="Add photos",
             optional_if_no_key="media_path",
             wait_seconds=2.0,
             notes="Large upload area. OCR fallback uses 'Add photos'. Opens OS file picker."),
        Step(number=6,
             description="OS file picker is open — click Open",
             action=ActionType.OS_OPEN,
             template="facebook_s7_open_button",
             text_fallback="Open",
             file_key="media_path",
             optional_if_no_key="media_path",
             wait_seconds=2.5,
             notes="Blue Open button in macOS file dialog."),
        Step(number=7,
             description="Click Post to publish",
             action=ActionType.CLICK,
             template="facebook_s8_post_button",
             text_fallback="BUP-Post",
             wait_seconds=60.0,
             bypass_swarm=True,
             notes="FINAL STEP: Uses the user's perfectly cropped 150x60 image template."),
        Step(number=8, description="Post published successfully", action=ActionType.CONFIRM_DONE),
    ]
)



# ─────────────────────────────────────────────────────────────────────────────
# LINKEDIN POST
# ─────────────────────────────────────────────────────────────────────────────
# CRITICAL STEP MAPPING:
# Step 2: click "Start a post" — opens composer
# Step 3: click photo icon (linkedin_photo_icon) — opens media picker
# Step 4: click Next (linkedin_next_button) — moves from picker to preview ← NOT Post
# Step 5: OS Open dialog → open file
# Step 6: click Done/Next after preview
# Step 7: click Post (linkedin_post_button) ← FINAL
LINKEDIN_POST = SocialFlow(
    task_id="linkedin_post",
    platform="linkedin",
    url="https://www.linkedin.com",
    description="Post on LinkedIn feed",
    steps=[
        Step(number=1, description="Open LinkedIn",
             action=ActionType.NAVIGATE, url="https://www.linkedin.com", wait_seconds=4.0),
        Step(number=2,
             description="Click 'Start a post' to open the composer",
             action=ActionType.CLICK,
             text_fallback="Start a post",
             wait_seconds=1.5,
             notes="Grey input bar at top of feed. OCR detects 'Start a post'."),
        Step(number=3,
             description="Click the photo/media icon in the composer toolbar",
             action=ActionType.CLICK,
             template="linkedin_photo_icon",
             text_fallback="Photo",
             optional_if_no_key="media_path",
             wait_seconds=1.5,
             notes="Opens the media file picker dialog."),
        Step(number=4,
             description="OS file picker is open — click Open",
             action=ActionType.OS_OPEN,
             template="linkedin_open_button",
             text_fallback="Open",
             file_key="media_path",
             optional_if_no_key="media_path",
             wait_seconds=2.5,
             notes="Blue Open button in macOS file dialog. This uploads the media."),
        Step(number=5,
             description="Click Next in the media preview modal",
             action=ActionType.CLICK,
             template=None,
             text_fallback="Next",
             optional_if_no_key="media_path",
             wait_seconds=60.0,
             bypass_swarm=True,
             notes="After selecting a file, LinkedIn shows a preview editor. You MUST click 'Next' here to return to the composer. Only do this if media was uploaded. Wait is 60s to allow videos to finish processing before the Next button appears."),
        Step(number=6,
             description="Type the post caption/text",
             action=ActionType.TYPE,
             type_text_key="caption",
             text_fallback="talk about",
             wait_seconds=1.0,
             notes="Click in the 'What do you want to talk about?' field to focus it, then type the caption."),
        Step(number=7,
             description="Click Post to publish",
             action=ActionType.CLICK,
             template="linkedin_post_button",
             text_fallback="Post",
             wait_seconds=3.0,
             bypass_swarm=True,
             notes="FINAL STEP: Blue Post button bottom right."),
        Step(number=8, description="Post published successfully", action=ActionType.CONFIRM_DONE),
    ]
)


# ─────────────────────────────────────────────────────────────────────────────
# X (TWITTER) POST
# ─────────────────────────────────────────────────────────────────────────────
X_POST = SocialFlow(
    task_id="x_post",
    platform="x",
    url="https://x.com",
    description="Post a tweet on X (Twitter)",
    steps=[
        Step(number=1, description="Open X",
             action=ActionType.NAVIGATE, url="https://x.com", wait_seconds=4.0),
        Step(number=2,
             description="Click the active black 'Post' button in the left sidebar to open the composer",
             action=ActionType.CLICK,
             template="x_s2_compose_icon",
             text_fallback="B-Post",
             wait_seconds=2.0,
             notes="Black rounded rectangle button with white 'Post' text in the left sidebar. Opens the tweet composer modal. The text box is auto-focused on open."),
        Step(number=3,
             description="Type the tweet text",
             action=ActionType.TYPE,
             type_text_key="tweet_text",
             wait_seconds=0.5,
             notes="Composer auto-focuses text box on open — type directly without clicking."),
        Step(number=4,
             description="(If media) Click the photo icon to attach image/video",
             action=ActionType.CLICK,
             template="x_s4_photo_icon",
             text_fallback="Photo",
             optional_if_no_key="media_path",
             wait_seconds=1.0,
             notes="Optional step. Only runs if media_path is provided."),
        Step(number=5,
             description="(If media) OS file picker — select and click Open",
             action=ActionType.OS_OPEN,
             text_fallback="Open",
             file_key="media_path",
             optional_if_no_key="media_path",
             wait_seconds=3.0,
             notes="Optional step. Opens Mac file picker and selects the vault media file."),
        Step(number=6,
             description="Click the Post button inside the composer to publish",
             action=ActionType.CLICK,
             template="x_s6_post_button",
             text_fallback="B-Post",
             wait_seconds=3.0,
             notes="FINAL STEP: Black Post button inside the composer."),
        Step(number=7, description="Tweet posted successfully", action=ActionType.CONFIRM_DONE),
    ]
)


# ─────────────────────────────────────────────────────────────────────────────
# FLOW REGISTRY — look up any flow by task_id
# ─────────────────────────────────────────────────────────────────────────────
FLOW_REGISTRY: dict[str, SocialFlow] = {
    flow.task_id: flow for flow in [
        WHATSAPP_STATUS,
        WHATSAPP_MESSAGE,
        INSTAGRAM_POST,
        INSTAGRAM_REEL,
        FACEBOOK_TEXT_POST,
        FACEBOOK_POST,
        LINKEDIN_POST,
        X_POST,
    ]
}


def detect_flow(user_text: str) -> Optional[SocialFlow]:
    """
    Given a user message, return the matching SocialFlow or None.
    Uses Tier-1 fuzzy parsing to catch misspelled variants and map them cleanly.
    """
    try:
        from bol.modules.m9_parser.command_parser import tier1_parser
        parsed = tier1_parser.parse(user_text)
        task_id = tier1_parser.map_to_task_id(parsed)
        
        if task_id:
            return FLOW_REGISTRY.get(task_id)
    except ImportError:
        pass
        
    return None
