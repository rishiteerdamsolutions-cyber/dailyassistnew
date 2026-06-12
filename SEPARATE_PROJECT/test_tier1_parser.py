from bol.modules.m9_parser.command_parser import tier1_parser
from bol.modules.m9_social.flows import detect_flow

test_cases = [
    ("text whsatapp", "whatsapp_status"),
    ("pic whatsapp", "whatsapp_status"),
    ("text and video whsatapp", "whatsapp_status"),
    ("put whtsap text", "whatsapp_status"),
    
    ("text instgrm", "instagram_post"),
    ("post image ig", "instagram_post"),
    ("vid insta", "instagram_post"),
    ("story pic insta", "instagram_post"), # Note: we just mapped to instagram_post currently, could add story flow later if needed
    
    ("fb txt", "facebook_text_post"),
    ("img fb", "facebook_post"),
    ("post text facebok", "facebook_text_post"),
    
    ("linkedin txt", "linkedin_post"),
    ("post image text linkdn", "linkedin_post"),
    
    ("tweet text", "x_post"),
    ("text twitter", "x_post"),
    ("x photo text", "x_post"),
    
    # Should not trigger flow:
    ("what is facebook", None),
    ("who are you", None),
]

print("Running Tier-1 Parser Tests...")
success_count = 0
for text, expected in test_cases:
    flow = detect_flow(text)
    actual_task_id = flow.task_id if flow else None
    
    if actual_task_id == expected:
        print(f"✅ PASS: '{text}' -> {expected}")
        success_count += 1
    else:
        print(f"❌ FAIL: '{text}' -> expected {expected}, got {actual_task_id}")
        # Debug why it failed
        parsed = tier1_parser.parse(text)
        print(f"   Parsed: {parsed}")

print(f"\nTest Results: {success_count} / {len(test_cases)} passed.")
