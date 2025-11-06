# utils/brand.py
# Centralized branding for Zephyra

# -------------------------------------------------
# Names & Titles
# -------------------------------------------------
NAME = "Zephyra"
INVITE_TITLE = f"Invite {NAME}"

# -------------------------------------------------
# Colors — with backward compatibility
# -------------------------------------------------
PRIMARY = 0x00E6F6
ACCENT  = PRIMARY
COLOR   = PRIMARY
PURPLE  = 0x9B5CFF  # secondary accent

# -------------------------------------------------
# Official Artwork Assets
# -------------------------------------------------
PROFILE_IMAGE = "https://cdn.discordapp.com/attachments/1435845031817904248/1435845594764673054/Zephyra_Profile.png?ex=690d72ea&is=690c216a&hm=45675e0235508512c807062d379ff5d9786241e9902d203a9460af838bb283d3&"
SERVER_BANNER = "https://cdn.discordapp.com/attachments/1435845031817904248/1435846183112413204/Zephyra_Server_banner.png?ex=690d7376&is=690c21f6&hm=f7e12b396e88b626a627f4c1c8fff3389c400dfa16afc08a3be8b780b4d69960&"

# -------------------------------------------------
# Emojis — your official custom set
# -------------------------------------------------
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
    """Quick emoji lookup w/ optional fallback."""
    return EMOJI.get(key, fallback)

# -------------------------------------------------
# Footer text
# -------------------------------------------------
FOOTER_DEV = "Zephyra — Developed by Polarix1954"