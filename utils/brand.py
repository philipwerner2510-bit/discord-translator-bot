# utils/brand.py
# ───────────────────────────────────────────────────────────
# ✅ Zephyra Branding Configuration (all exports consolidated)
# ───────────────────────────────────────────────────────────

# — Names
NAME = "Zephyra"

# — Colors
COLOR  = 0x00E6F6          # primary cyan
ACCENT = COLOR             # alias for cogs importing ACCENT
PURPLE = 0x9B5CFF          # optional secondary accent

# ───────────────────────────────────────────────────────────
# ✅ Official Assets (exact URLs you provided)
# ───────────────────────────────────────────────────────────
PROFILE_IMAGE = "https://cdn.discordapp.com/attachments/1435845031817904248/1435845594764673054/Zephyra_Profile.png?ex=690d72ea&is=690c216a&hm=45675e0235508512c807062d379ff5d9786241e9902d203a9460af838bb283d3&"
SERVER_BANNER = "https://cdn.discordapp.com/attachments/1435845031817904248/1435846183112413204/Zephyra_Server_banner.png?ex=690d7376&is=690c21f6&hm=f7e12b396e88b626a627f4c1c8fff3389c400dfa16afc08a3be8b780b4d69960&"

# Back-compat aliases some cogs expect
AVATAR_URL        = PROFILE_IMAGE
PROFILE_IMAGE_URL = PROFILE_IMAGE
SERVER_BANNER_URL = SERVER_BANNER
BOT_BANNER_URL    = SERVER_BANNER

# ───────────────────────────────────────────────────────────
# ✅ Titles
# ───────────────────────────────────────────────────────────
HELP_TITLE    = f"{NAME} Help"
GUIDE_TITLE   = f"Getting Started with {NAME}"
INVITE_TITLE  = f"Invite {NAME}"
WELCOME_TITLE = f"Welcome — {NAME}"
STATS_TITLE   = f"{NAME} Statistics"

# ───────────────────────────────────────────────────────────
# ✅ Footer text (string + callable aliases for old code)
# ───────────────────────────────────────────────────────────
FOOTER_DEV       = "Zephyra — Developed by Polarix1954"
FOOTER_TEXT      = FOOTER_DEV           # some cogs import this name
FOOTER_TRANSLATED = FOOTER_DEV          # used in translate embeds

def footer_text() -> str:
    """Some cogs expect a function named footer_text()."""
    return FOOTER_DEV

def footer() -> str:
    """Some cogs call footer() like a function."""
    return FOOTER_DEV

# ───────────────────────────────────────────────────────────
# ✅ Custom Emojis (update IDs only if you re-upload)
# ───────────────────────────────────────────────────────────
Z_BASE     = "<:Zephyra:1435530499408924672>"
Z_ANGRY    = "<:Zephyra_angry:1435525299692372051>"
Z_CONFUSED = "<:Zephyra_confused:1435525352142274561>"
Z_EXCITED  = "<:Zephyra_excited:1435525400364322847>"
Z_HAPPY    = "<:Zephyra_happy:1435530725041504323>"
Z_LOVE     = "<:Zephyra_love:1435525377081479229>"
Z_SAD      = "<:Zephyra_sad:1435530792934572052>"
Z_SHY      = "<:Zephyra_shy:1435525324627640361>"
Z_TIRED    = "<:Zephyra_tired:1435525424422719518>"

EMOJI = {
    "base":     Z_BASE,
    "angry":    Z_ANGRY,
    "confused": Z_CONFUSED,
    "excited":  Z_EXCITED,
    "happy":    Z_HAPPY,
    "love":     Z_LOVE,
    "sad":      Z_SAD,
    "shy":      Z_SHY,
    "tired":    Z_TIRED,
}

def e(key: str, fallback: str = "") -> str:
    """Lookup helper: e('happy') -> custom emoji string."""
    return EMOJI.get(key, fallback)

ALL_Z_EMOJIS = [
    Z_HAPPY, Z_EXCITED, Z_LOVE, Z_SHY,
    Z_CONFUSED, Z_SAD, Z_TIRED, Z_ANGRY, Z_BASE
]

# ───────────────────────────────────────────────────────────
# ✅ Presence Template
# ───────────────────────────────────────────────────────────
PRESENCE_TEMPLATE = "{servers} servers • {translations} translations today"
