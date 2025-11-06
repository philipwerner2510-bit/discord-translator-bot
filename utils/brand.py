# utils/brand.py
# Centralized branding for Zephyra

# --- Names & Titles
NAME = "Zephyra"
INVITE_TITLE = f"Invite {NAME}"
WELCOME_TITLE = f"Welcome — {NAME}"
HELP_TITLE = f"{NAME} Help"

# --- Colors (with backward-compat aliases)
PRIMARY = 0x00E6F6
ACCENT  = PRIMARY
COLOR   = PRIMARY
PURPLE  = 0x9B5CFF  # optional secondary accent

# --- Official Artwork Assets (your URLs)
PROFILE_IMAGE = "https://cdn.discordapp.com/attachments/1435845031817904248/1435845594764673054/Zephyra_Profile.png?ex=690d72ea&is=690c216a&hm=45675e0235508512c807062d379ff5d9786241e9902d203a9460af838bb283d3&"
SERVER_BANNER = "https://cdn.discordapp.com/attachments/1435845031817904248/1435846183112413204/Zephyra_Server_banner.png?ex=690d7376&is=690c21f6&hm=f7e12b396e88b626a627f4c1c8fff3389c400dfa16afc08a3be8b780b4d69960&"

# Backward-compat aliases some cogs expect:
PROFILE_IMAGE_URL  = PROFILE_IMAGE
SERVER_BANNER_URL  = SERVER_BANNER
BOT_BANNER_URL     = SERVER_BANNER  # same banner asset as server
AVATAR_URL    =PROFILE_IMAGE
# --- Footer text
FOOTER_DEV = "Zephyra — Developed by Polarix1954"
footer = FOOTER_DEV
def footer_text() -> str:
    return FOOTER_DEV

# Some cogs expect a separate translated footer; map it to the dev footer
FOOTER_TRANSLATED = FOOTER_DEV

# --- Custom Emojis (your official set)
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
    return EMOJI.get(key, fallback)

# Per-emoji aliases some cogs import directly
Z_BASE     = EMOJI["base"]
Z_ANGRY    = EMOJI["angry"]
Z_CONFUSED = EMOJI["confused"]
Z_EXCITED  = EMOJI["excited"]
Z_HAPPY    = EMOJI["happy"]
Z_LOVE     = EMOJI["love"]
Z_SAD      = EMOJI["sad"]
Z_SHY      = EMOJI["shy"]
Z_TIRED    = EMOJI["tired"]
