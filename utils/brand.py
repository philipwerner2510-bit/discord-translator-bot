# utils/brand.py
# Central brand strings, emojis & assets for Zephyra.

# ——— Basics ———
NAME: str = "Zephyra"
COLOR: int = 0x00E6F6            # main aqua
ACCENT: int = 0x7C4DFF           # soft purple

# ——— Footer text ———
FOOTER_TEXT: str = "Zephyra — Developed by Polarix1954"

# Back-compat alias some cogs import
footer_text: str = FOOTER_TEXT

def footer() -> str:
    """Return the standard footer text."""
    return FOOTER_TEXT

# Used by translate embeds (“clean but with footer” per your spec)
FOOTER_TRANSLATED: str = "Translated by Zephyra — Developed by Polarix1954"

# ——— Titles / copy ———
HELP_TITLE: str = "Zephyra — Commands"
WELCOME_TITLE: str = "Welcome to the server!"
INVITE_TITLE: str = "Invite Zephyra"
PROFILE_TITLE: str = "Profile"
LEADERBOARD_TITLE: str = "Leaderboard"

# ——— Image assets (your CDN links) ———
AVATAR_URL: str = (
    "https://cdn.discordapp.com/attachments/1435845031817904248/1435845594764673054/"
    "Zephyra_Profile.png?ex=690d72ea&is=690c216a&hm=45675e0235508512c807062d379ff5d9786241e9902d203a9460af838bb283d3&"
)
SERVER_BANNER_URL: str = (
    "https://cdn.discordapp.com/attachments/1435845031817904248/1435846183112413204/"
    "Zephyra_Server_banner.png?ex=690d7376&is=690c21f6&hm=f7e12b396e88b626a627f4c1c8fff3389c400dfa16afc08a3be8b780b4d69960&"
)
BOT_BANNER_URL: str = SERVER_BANNER_URL  # same banner

# ——— Custom medals (numbers-only, Zephyra style) ———
MEDAL_1: str = "<:Zephyra_emote_1:1436100371058790431>"  # gold
MEDAL_2: str = "<:Zephyra_emote_2:1436100410292043866>"  # silver
MEDAL_3: str = "<:Zephyra_emote_3:1436100442571669695>"  # bronze

def medal_for_rank(rank: int) -> str:
    if rank == 1: return MEDAL_1
    if rank == 2: return MEDAL_2
    if rank == 3: return MEDAL_3
    return f"#{rank}"

# ——— Zephyra emoji set (optional) ———
Z_HAPPY: str    = "<:Zephyra_happy:143552753652287560>"
Z_LOVE: str     = "<:Zephyra_love:1435527693528465408>"
Z_SAD: str      = "<:Zephyra_sad:1435530792934572052>"
Z_ANGRY: str    = "<:Zephyra_angry:1435527551815782451>"
Z_CONFUSED: str = "<:Zephyra_confused:1435527598355779597>"
Z_TIRED: str    = "<:Zephyra_tired:1435525424422719518>"
Z_EXCITED: str  = "<:Zephyra_excited:1435525400364322847>"
Z_BASE: str     = "<:Zephyra:1435527391438045204>"
