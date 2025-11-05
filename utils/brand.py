# utils/brand.py
NAME = "Zephyra"

# Brand color (Storm-Cyan)
COLOR = 0x00E6F6

# Custom emojis (your IDs only)
EMOJI_PRIMARY  = "<:Zephyra_happy:1435530725041504323>"      # branding + footer
EMOJI_THINKING = "<:Zephyra_confused:1435525352142274561>"   # thinking/processing
EMOJI_HIGHLIGHT= "<:Zephyra_excited:1435525400364322847>"    # headers/highlights
EMOJI_ACCENT   = "<:Zephyra:1435530499408924672>"            # identity/wind accent

# Footer text for all embeds
def footer() -> str:
    return f"{EMOJI_PRIMARY} Zephyra • by @Polarix1954"

# Presence line template (bot rotates through several; see bot.py)
PRESENCE_TEMPLATE = f"{EMOJI_ACCENT} Serving {{servers}} servers • {{translations}} translations today"