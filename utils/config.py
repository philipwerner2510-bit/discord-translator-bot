import os
import json

CONFIG_FILE = os.getenv("BOT_CONFIG_PATH", "config.json")

SUPPORTED_LANGS = []
CONFIG = None

# Pretty metadata for language codes (flag + human name)
LANG_META = {
    "en": ("🇬🇧", "English"),
    "zh": ("🇨🇳", "Chinese"),
    "hi": ("🇮🇳", "Hindi"),
    "es": ("🇪🇸", "Spanish"),
    "fr": ("🇫🇷", "French"),
    "ar": ("🇸🇦", "Arabic"),
    "bn": ("🇧🇩", "Bengali"),
    "pt": ("🇵🇹", "Portuguese"),
    "ru": ("🇷🇺", "Russian"),
    "ja": ("🇯🇵", "Japanese"),
    "de": ("🇩🇪", "German"),
    "jv": ("🇮🇩", "Javanese"),
    "ko": ("🇰🇷", "Korean"),
    "vi": ("🇻🇳", "Vietnamese"),
    "mr": ("🇮🇳", "Marathi"),
    "ta": ("🇮🇳", "Tamil"),
    "ur": ("🇵🇰", "Urdu"),
    "tr": ("🇹🇷", "Turkish"),
    "it": ("🇮🇹", "Italian"),
    "th": ("🇹🇭", "Thai"),
    "gu": ("🇮🇳", "Gujarati"),
    "kn": ("🇮🇳", "Kannada"),
    "ml": ("🇮🇳", "Malayalam"),
    "pa": ("🇮🇳", "Punjabi"),
    "or": ("🇮🇳", "Odia"),
    "fa": ("🇮🇷", "Persian"),
    "sw": ("🇰🇪", "Swahili"),
    "am": ("🇪🇹", "Amharic"),
    "ha": ("🇳🇬", "Hausa"),
    "yo": ("🇳🇬", "Yoruba"),
}

def lang_label(code: str) -> str:
    """Return '🇬🇧 English (en)' style label for a code."""
    flag, name = LANG_META.get(code, ("🌐", code.upper()))
    if isinstance(name, tuple):  # just in case
        name = name[0]
    return f"{flag} {name} ({code})"

class Config:
    def __init__(self, data):
        self.default_rate_limit = data.get("default_rate_limit", 5)
        self.reaction_timeout = data.get("reaction_timeout", 300)

def load_config():
    global CONFIG, SUPPORTED_LANGS
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        CONFIG = Config(data)
        SUPPORTED_LANGS = data.get("supported_langs", [])
        # ensure meta exists for all supported codes
        for c in SUPPORTED_LANGS:
            LANG_META.setdefault(c, ("🌐", c.upper()))
        print("✅ Config loaded.")
    except Exception as e:
        print(f"⚠️ Failed to load config: {e}")
        CONFIG = Config({})
        SUPPORTED_LANGS = ["en"]
        LANG_META.setdefault("en", ("🇬🇧", "English"))

load_config()