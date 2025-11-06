# utils/brand.py
# — Centralized branding for Zephyra (backward-compatible) —

# ===== Names & Titles =====
NAME = "Zephyra"

INVITE_TITLE  = f"Invite {NAME}"
WELCOME_TITLE = f"Welcome — {NAME}"
HELP_TITLE    = f"{NAME} Help"
GUIDE_TITLE   = f"Getting Started with {NAME}"

# ===== Colors =====
PRIMARY = 0x00E6F6          # main embed color (storm cyan)
ACCENT  = PRIMARY           # alias used by some cogs
COLOR   = PRIMARY           # legacy alias for older imports
PURPLE  = 0x9B5CFF          # secondary accent if needed

# ===== Footer text =====
FOOTER_DEV = f"{NAME} — Developed by Polarix1954"

def footer(*_args, **_kwargs) -> str:
    """
    Backward-compatible helper some cogs import as a function.
    We no longer put emojis in footers (Discord won’t render custom ones in footers).
    """
    return FOOTER_DEV

# ===== Custom emojis (uploaded to your app/user) =====
EMOJI = {
    "base":     "<:Zephyra:1435530499408924672>",
    "angry":    "<:Zephyra_angry:1435525299692372051>",
    "confused": "<:Zephyra_confused:1435525352142274561>",
    "excited":  "<:Zephyra_excited:1435525400364322847>",
    "happy":    "<:Zephyra_happy:1435530725041504323>",
    "love":     "<:Zephyra_love:1435525377081479229>",
    "sad":      "<:Zephyra_sad:1435530792934572052>",
    "shy":      "<:Zephyra_shy:1435525324627640361>",
    "tired":    "<:Zephyra_tired:1435525424422719518>",
}

def e(key: str, fallback: str = "") -> str:
    """Return a custom emoji string by key, or fallback if missing."""
    return EMOJI.get(key, fallback)
