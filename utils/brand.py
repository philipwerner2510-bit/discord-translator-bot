# utils/brand.py
NAME = "Zephyra"
COLOR = 0x00E6F6  # Storm-cyan

# Your custom Zephyra emojis
ZEPHYRA_EMOJIS = {
    "base":     "<:Zephyra:1435530499408924672>",
    "happy":    "<:Zephyra_happy:1435530725041504323>",
    "confused": "<:Zephyra_confused:1435525352142274561>",
    "excited":  "<:Zephyra_excited:1435525400364322847>",
    "love":     "<:Zephyra_love:1435525377081479229>",
    "angry":    "<:Zephyra_angry:1435525299692372051>",
    "sad":      "<:Zephyra_sad:1435530792934572052>",
    "shy":      "<:Zephyra_shy:1435525324627640361>",
    "tired":    "<:Zephyra_tired:1435525424422719518>",
}

def emote(key: str, default: str = "") -> str:
    return ZEPHYRA_EMOJIS.get(key, default)

# Back-compat aliases used by cogs
EMOJI_PRIMARY   = emote("happy")     # titles / branding
EMOJI_HIGHLIGHT = emote("excited")   # section headers
EMOJI_ACCENT    = emote("base")      # subtle accent
EMOJI_THINKING  = emote("confused")  # loading
EMOJI_SUCCESS   = emote("love")      # success (non-footer)
EMOJI_ERROR     = emote("angry")     # errors
EMOJI_WARN      = emote("shy")       # soft warning
EMOJI_SAD       = emote("sad")       # failures
EMOJI_TIRED     = emote("tired")     # cooldown

def footer() -> str:
    # No emojis in footer (Discord doesn’t render customs there reliably)
    return "Zephyra • by @Polarix1954"

# Presence (rotate in bot.py if desired)
PRESENCE_LINES = [
    f"{EMOJI_ACCENT} Serving {{servers}} servers • {{translations}} translations today",
    "Assisting live translations",
    "Standing by",
]
PRESENCE_TEMPLATE = "Serving {servers} servers • {translations} translations today"