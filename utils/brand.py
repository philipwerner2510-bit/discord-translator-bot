# utils/brand.py
# Centralized branding for Zephyra

# --- Names & titles
NAME = "Zephyra"
INVITE_TITLE = f"Invite {NAME}"

# --- Colors
PRIMARY = 0x00E6F6          # storm-cyan (main embed color)
ACCENT = PRIMARY            # many cogs import ACCENT; keep as alias
PURPLE = 0x9B5CFF           # subtle accent if needed

# --- Footer text
FOOTER_DEV = "Zephyra — Developed by Polarix1954"

# --- Emojis (your uploaded custom emojis)
# Tip: keep these in one place so embeds/buttons can reference them safely
EMOJI = {
    "base":         "<:Zephyra:1435530499408924672>",
    "angry":        "<:Zephyra_angry:1435525299692372051>",
    "confused":     "<:Zephyra_confused:1435525352142274561>",
    "excited":      "<:Zephyra_excited:1435525400364322847>",
    "happy":        "<:Zephyra_happy:1435530725041504323>",
    "love":         "<:Zephyra_love:1435525377081479229>",
    "sad":          "<:Zephyra_sad:1435530792934572052>",
    "shy":          "<:Zephyra_shy:1435525324627640361>",
    "tired":        "<:Zephyra_tired:1435525424422719518>",
}

def e(key: str, fallback: str = "") -> str:
    """Return a custom emoji string by key, or fallback if missing."""
    return EMOJI.get(key, fallback)
