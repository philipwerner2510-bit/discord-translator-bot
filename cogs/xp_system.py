# cogs/xp_system.py
import math
import discord
from discord.ext import commands
from discord import app_commands

from utils.brand import COLOR, NAME  # keep brand usage minimal
from utils import database

# ------- Level math (simple & readable) -------
LEVEL_STEP = 100  # XP needed for each new level (constant steps)

def split_level(total_xp: int):
    """Return (level, cur_in_level, next_needed, pct) for a constant step curve."""
    total_xp = max(0, int(total_xp))
    level = total_xp // LEVEL_STEP
    cur = total_xp % LEVEL_STEP
    nxt = LEVEL_STEP
    pct = 0 if nxt == 0 else int((cur / nxt) * 100)
    return level, cur, nxt, pct

# ------- Bar builder (Style A, softer fill, slightly shorter) -------
# Layout:
# ▓ = filled, ▯ = empty
#  top row: 12 cells
# bottom row: 10 cells (indented by one space to mimic tilt)
TOP_CELLS = 12
BOT_CELLS = 10
FILLED = "▓"
EMPTY  = "▯"

def build_tilt_bar(cur: int, nxt: int):
    """Two-line, slightly slanted bar. Returns (line1, line2)."""
    total_cells = TOP_CELLS + BOT_CELLS
    # guard
    cur = max(0, min(cur, max(1, nxt)))
    filled_cells = 0 if nxt <= 0 else int(round((cur / nxt) * total_cells))

    top_fill = min(filled_cells, TOP_CELLS)
    bot_fill = max(0, filled_cells - TOP_CELLS)

    top_line = FILLED * top_fill + EMPTY * (TOP_CELLS - top_fill)
    bot_line = FILLED * bot_fill + EMPTY * (BOT_CELLS - bot_fill)

    # Add one leading space on bottom to suggest the tilt/offset
    return top_line, f" {bot_line}"

# ------- Cog -------
class XpSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # This event lets other cogs notify us after XP changes (e.g., translations)
    @commands.Cog.listener("on_xp_gain")
    async def _on_xp_gain(self, guild_id: int, user_id: int):
        # no live UI push here (keeps this lightweight)
        return

    # Public: /profile
    @app_commands.command(name="profile", description="Show your Zephyra XP profile.")
    @app_commands.describe(member="Show another member's profile")
    async def xp_profile(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        gid = interaction.guild.id

        # read totals
        total_xp, messages, translations, voice_seconds = await database.get_xp(gid, member.id)
        level, cur, nxt, pct = split_level(total_xp)

        # build the tilted bar
        bar_top, bar_bot = build_tilt_bar(cur, nxt)

        # compact voice time display
        h = voice_seconds // 3600
        m = (voice_seconds % 3600) // 60

        # header & body
        e = discord.Embed(color=COLOR, title=f"{member.display_name}'s Profile")
        e.add_field(name="Level:", value=f"**{level}**", inline=False)
        e.add_field(name="XP:", value=f"**{cur}**  •  Next: **{cur}/{nxt} ({pct}%)**", inline=False)

        # show the two-line progress bar in a code block to keep monospaced tilt
        bar_block = f"```\n{bar_top}\n{bar_bot}\n```"
        e.add_field(name="\u200b", value=bar_block, inline=False)

        # stats row — same order/labels as your screenshot
        e.add_field(name="Messages", value=f"**{messages}**", inline=True)
        e.add_field(name="Translations", value=f"**{translations}**", inline=True)
        e.add_field(name="Voice Time", value=f"**{h}h  {m}m**", inline=True)

        # avatar on the right
        try:
            e.set_thumbnail(url=member.display_avatar.replace(format="png", size=256).url)
        except Exception:
            e.set_thumbnail(url=member.display_avatar.url)

        # footer (no brand import churn)
        e.set_footer(text=f"{NAME} — Developed by Polarix1954")

        await interaction.response.send_message(embed=e)

async def setup(bot):
    await bot.add_cog(XpSystem(bot))
