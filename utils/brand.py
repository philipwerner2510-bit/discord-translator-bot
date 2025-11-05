# utils/brand.py
NAME = "Zephyra"
COLOR = 0x00E6F6  # Storm-cyan

# ── Your custom Zephyra emojis (IDs from your list) ────────────────────────────
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
    """Get a Zephyra emoji by key; safe if missing."""
    return ZEPHYRA_EMOJIS.get(key, default)

# ── Back-compat aliases (so existing cogs keep working) ───────────────────────
# Branding / sections
EMOJI_PRIMARY   = emote("happy")     # general branding icon in titles
EMOJI_HIGHLIGHT = emote("excited")   # section headers / highlights
EMOJI_ACCENT    = emote("base")      # subtle accent / identity

# States
EMOJI_THINKING  = emote("confused")  # “translating…” / busy
EMOJI_SUCCESS   = emote("love")      # success confirmations (non-footer)
EMOJI_ERROR     = emote("angry")     # errors
EMOJI_WARN      = emote("shy")       # soft warnings / “heads up”
EMOJI_SAD       = emote("sad")       # failures / not found
EMOJI_TIRED     = emote("tired")     # rate-limited / cooldown

# ── Footer text (no emojis here—Discord doesn’t render custom emotes in footers)
def footer() -> str:
    return "Zephyra • by @Polarix1954"

# ── Presence templates (rotate these in bot.py if you want) ───────────────────
PRESENCE_LINES = [
    f"{EMOJI_ACCENT} Serving {{servers}} servers • {{translations}} translations today",
    f"{EMOJI_HIGHLIGHT} Helping across languages",
    f"{EMOJI_THINKING} Standing by",
]
# Or single template if you prefer one line everywhere:
PRESENCE_TEMPLATE = "Serving {servers} servers • {translations} translations today"