import re
import difflib
from typing import Optional, Dict, List, Tuple, Any

# Pre-defined dictionaries of aliases
PLATFORMS = {
    "whatsapp": ["whatsapp", "watsap", "whsatapp", "whasap", "wahtsapp", "whtsapp", "wapp", "wahtsap", "wtsap", "whstapp", "whtsp", "wa", "whatsap", "watsapp", "wtsp", "watsp", "whtap"],
    "instagram": ["instagram", "insta", "instgrm", "instgram", "ig", "instrm", "instagam", "instagrm", "intagram", "inst"],
    "facebook": ["facebook", "fb", "fcbk", "facebok", "facebk", "fcebk", "acebok", "facebkok", "fcbook", "fbook", "faceboook", "fbc"],
    "linkedin": ["linkedin", "linkdin", "linkdn", "li", "linkd in", "linked in", "lnkdin", "lkin", "linkden", "linkin"],
    "x": ["x", "twitter", "x.com", "tweet", "twiter", "twtter", "twitr", "twt", "twtr"]
}

MEDIA_TYPES = {
    "text": ["text", "txt", "msg", "caption", "message", "say"],
    "image": ["image", "img", "pic", "photo", "picture"],
    "video": ["video", "vid", "vdo", "reel", "clip", "mp4"]
}

ACTIONS = {
    "status": ["status", "story"],
    "post": ["post", "share", "upload", "put", "update", "drop", "add", "send"],
    "message": ["dm", "pm", "message", "reply"]
}

def build_reverse_map(d: Dict[str, List[str]]) -> Dict[str, str]:
    """Builds a flat dictionary mapping every alias to its canonical term."""
    reverse_map = {}
    for canonical, aliases in d.items():
        # Always include the canonical word itself
        reverse_map[canonical] = canonical
        for alias in aliases:
            reverse_map[alias.lower()] = canonical
    return reverse_map

PLATFORM_MAP = build_reverse_map(PLATFORMS)
MEDIA_MAP = build_reverse_map(MEDIA_TYPES)
ACTION_MAP = build_reverse_map(ACTIONS)

class CommandParser:
    """
    Tier-1 No-AI Command Parser.
    Extracts platform, action, and media type from user text, including handling misspellings via fuzzy matching.
    """
    
    def __init__(self, cutoff: float = 0.8):
        self.cutoff = cutoff
        self.all_platforms = list(PLATFORM_MAP.keys())
        self.all_media = list(MEDIA_MAP.keys())
        self.all_actions = list(ACTION_MAP.keys())
        
    def _fuzzy_match(self, word: str, pool: List[str]) -> Optional[str]:
        # Exact match first
        if word in pool:
            return word
        # Fuzzy match
        matches = difflib.get_close_matches(word, pool, n=1, cutoff=self.cutoff)
        return matches[0] if matches else None

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parses the text and returns a structured dictionary of what was found.
        """
        # Clean text: lowercase, remove punctuation except for letters/numbers
        clean_text = re.sub(r'[^a-z0-9\s\.]', ' ', text.lower())
        words = clean_text.split()
        
        found_platform = None
        found_media = set()
        found_action = None
        
        # 1. Platform Detection
        for word in words:
            # Don't try to fuzzy match platform if it's explicitly an exact media or action keyword
            if word in MEDIA_MAP or word in ACTION_MAP:
                continue
            match = self._fuzzy_match(word, self.all_platforms)
            if match:
                found_platform = PLATFORM_MAP[match]
                break
                
        # 2. Media Detection
        for word in words:
            if word in PLATFORM_MAP or word in ACTION_MAP:
                continue
            match = self._fuzzy_match(word, self.all_media)
            if match:
                found_media.add(MEDIA_MAP[match])
                
        # 3. Action Detection
        for word in words:
            if word in PLATFORM_MAP or word in MEDIA_MAP:
                continue
            match = self._fuzzy_match(word, self.all_actions)
            if match:
                found_action = ACTION_MAP[match]
                break
                
        return {
            "success": bool(found_platform), # Minimum requirement is finding a platform
            "platform": found_platform,
            "media_types": list(found_media),
            "action": found_action,
            "raw_text": text
        }
        
    def map_to_task_id(self, parsed: Dict) -> Optional[str]:
        """
        Maps the parsed attributes to our internal Flow Registry task_ids.
        Returns None if it can't map it reliably.
        """
        if not parsed["success"]:
            return None
            
        plat = parsed["platform"]
        media = parsed["media_types"]
        act = parsed["action"]
        
        # REQUIRE an action OR a media type to prevent generic questions like "what is facebook?" from triggering a post.
        # EXCEPTION: some platform keywords inherently imply an action (e.g. "tweet" = post on X)
        IMPLICIT_POST_PLATFORMS = {"tweet", "story", "reel"}
        raw_lower = parsed.get("raw_text", "").lower()
        raw_words = set(raw_lower.split())
        
        # If the platform was detected via a word that implies posting, infer the action
        if not act and raw_words & IMPLICIT_POST_PLATFORMS:
            act = "post"
        
        # If platform detected + remaining words look like content (not just the platform name),
        # assume the user wants to post that content
        if not act and not media:
            STOP_WORDS = {"what", "who", "how", "why", "when", "where", "does", "the", "this", "that", "can", "will", "about", "with", "from", "have", "has", "are", "was", "were", "for"}
            non_platform_words = [w for w in raw_lower.split() if w not in PLATFORM_MAP and w not in STOP_WORDS and len(w) > 2]
            if non_platform_words:
                act = "post"
        
        if not act and not media:
            return None
            
        # WhatsApp mapping
        if plat == "whatsapp":
            if act == "message":
                return "whatsapp_message"
            # Default to status if they say post, status, or just mention media on whatsapp
            return "whatsapp_status"
            
        # Instagram mapping
        elif plat == "instagram":
            if "video" in media and (act == "post" or act == "status" or not act):
                # We could distinguish reel vs post based on 'reel' keyword, but let's check raw_text
                if "reel" in parsed["raw_text"].lower():
                    return "instagram_reel"
            return "instagram_post"
            
        # Facebook mapping
        elif plat == "facebook":
            # If they exclusively say text and no image/video, map to facebook_text_post
            if "text" in media and "image" not in media and "video" not in media:
                return "facebook_text_post"
            # If they don't specify media, default to standard post (can handle text-only too, but text_post is specific)
            if not media and act in ["post", "status"]:
                 return "facebook_text_post"
            return "facebook_post"
            
        # LinkedIn mapping
        elif plat == "linkedin":
            return "linkedin_post"
            
        # X / Twitter mapping
        elif plat == "x":
            return "x_post"
            
        return None

# Singleton instance
tier1_parser = CommandParser()
