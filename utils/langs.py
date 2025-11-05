# utils/langs.py

LANG_INFO = {
    "en": ("🇬🇧", "English"), "zh": ("🇨🇳", "Mandarin Chinese"),
    "hi": ("🇮🇳", "Hindi"), "es": ("🇪🇸", "Spanish"),
    "fr": ("🇫🇷", "French"), "ar": ("🇸🇦", "Arabic"),
    "bn": ("🇧🇩", "Bengali"), "pt": ("🇵🇹", "Portuguese"),
    "ru": ("🇷🇺", "Russian"), "ja": ("🇯🇵", "Japanese"),
    "de": ("🇩🇪", "German"), "jv": ("🇮🇩", "Javanese"),
    "ko": ("🇰🇷", "Korean"), "vi": ("🇻🇳", "Vietnamese"),
    "mr": ("🇮🇳", "Marathi"), "ta": ("🇮🇳", "Tamil"),
    "ur": ("🇵🇰", "Urdu"), "tr": ("🇹🇷", "Turkish"),
    "it": ("🇮🇹", "Italian"), "th": ("🇹🇭", "Thai"),
    "gu": ("🇮🇳", "Gujarati"), "kn": ("🇮🇳", "Kannada"),
    "ml": ("🇮🇳", "Malayalam"), "pa": ("🇮🇳", "Punjabi"),
    "or": ("🇮🇳", "Odia"), "fa": ("🇮🇷", "Persian"),
    "sw": ("🇰🇪", "Swahili"), "am": ("🇪🇹", "Amharic"),
    "ha": ("🇳🇬", "Hausa"), "yo": ("🇳🇬", "Yoruba"),
}

SUPPORTED_LANGS = list(LANG_INFO.keys())

def lang_label(code: str) -> str:
    flag, name = LANG_INFO.get(code, ("🏳️", "Unknown"))
    return f"{flag} {code} — {name}"