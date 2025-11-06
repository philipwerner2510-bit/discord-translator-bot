# utils/brand.py
# — Centralized branding for Zephyra (full, updated) —

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

# ===== Optional image assets (Discord CDN links recommended) =====
# You can paste your CDN URLs here for richer embeds.
AVATAR_URL       = "https://cdn.discordapp.com/attachments/1435845031817904248/1435845594764673054/Zephyra_Profile.png?ex=690d72ea&is=690c216a&hm=45675e0235508512c807062d379ff5d9786241e9902d203a9460af838bb283d3&"  # Left image you sent (profile picture) — optional
SERVER_BANNER_URL= "https://cdn.discordapp.com/attachments/1435845031817904248/1435846183112413204/Zephyra_Server_banner.png?ex=690d7376&is=690c21f6&hm=f7e12b396e88b626a627f4c1c8fff3389c400dfa16afc08a3be8b780b4d69960&"  # Middle (server banner) — optional
BOT_BANNER_URL   = "https://cdn.discordapp.com/attachments/1435845031817904248/1435845190203080764/file_00000000e9a071f494aebc9b33f74fac.png?ex=690d728a&is=690c210a&hm=040f50c7b940d2448e2b91de3671a466155bfa8d1d85903d3cc709d750f88eb8&"  # Right (bot profile banner) — optional

# ===== Footer text =====
FOOTER_DEV = f"{NAME} — Developed by Polarix1954"
FOOTER_TRANSLATED = f"Translated by {NAME}"

def footer(*_args, **_kwargs) -> str:
    """Discord won't render custom emojis in footers; keep it text-only."""
    return FOOTER_DEV

# ===== Custom emojis (raw markup) =====
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
    """Return a custom emoji string by key, fallback if missing."""
    return EMOJI.get(key, fallback)

# ===== Backwards-compat emoji constants =====
Z_EXCITED  = e("excited")
Z_TIRED    = e("tired")
Z_CONFUSED = e("confused")
Z_SAD      = e("sad")
Z_HAPPY    = e("happy")
Z_LOVE     = e("love")
Z_ANGRY    = e("angry")
Z_BASE     = e("base")
