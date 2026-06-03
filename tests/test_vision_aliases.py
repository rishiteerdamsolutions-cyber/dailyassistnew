"""Vision button template alias coverage."""

from bol.modules.m3_visual.vision_buttons import VisionButtonLibrary


def test_whatsapp_text_status_icon_alias_loaded():
    lib = VisionButtonLibrary()
    assert "whatsapp_new_status_icon" in lib._cache
    assert "whatsapp_text_status_icon" in lib._cache
