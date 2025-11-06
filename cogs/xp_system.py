# cogs/xp_system.py
# Pretty /profile with avatar + XP progress bar (no leaderboard here)

import math
from typing import Optional

import discord
from discord.ext import commands
from discord import app_commands

from utils import database
from utils.brand import COLOR, footer_text, Z_HAPPY, NAME


# ------ Leveling curve helpers ------

def level_from_xp(total_xp: int) -> int:
    """
    Smooth curve:
      xp_to_reach_level(n) = 100 * n^1.5  (rounded)
    Invert to get level from total_xp.
    """
    if total_xp <= 0:
        return 0
    # Solve n from xp = 100 * n^1.5  -> n = (xp/100)^(2/3)
    n = (max(0, total_xp) / 100.0) ** (2.0 / 3.0)
    return int(n)


def xp_for_level(level: int) -> int:
    """XP required to REACH this level (cumulative)."""
    if level <= 0:
        return 0
    return int(round(100.0 * (level ** 1.5)))


def xp_to_next_level(total_xp: int) -> tuple[int, int, int]:
    """
    Returns (current_level, xp_into_level, xp_needed_for_levelup)
    """
    lvl = level_from_xp(total_xp)
    base = xp_for_level(lvl)
    nxt = xp_for_level(lvl + 1)
    into = total_xp - base
    need = max(1, nxt - base)
    return lvl, max(0, into), need


def make_progress_bar(into: int, need: int, width: int = 22) -> str:
    """
    Text progress bar suitable for embeds.
    Uses block characters for readability at small sizes.
    """
    ratio = 0 if need <= 0 else max(0.0, min(1.0, into / need))
    filled = int(round(ratio * width))
    empty = max(0, width - filled)
    return "▰" * filled + "▱" * empty


# ------ Cog ------

class XpSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="profile", description="Show a user's XP profile (level, progress, stats).")
    @app_commands.describe(user="Whose profile to view (optional).")
    async def xp_profile(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        member = user or interaction.user
        gid = interaction.guild.id if interaction.guild else 0

        # Fetch XP stats
        xp, msgs, trans, vsec = await database.get_xp(gid, member.id)

        # Level math
        lvl, into, need = xp_to_next_level(xp)
        bar = make_progress_bar(into, need, width=22)
        pct = 0 if need == 0 else int((into / need) * 100)

        # Build embed
        e = discord.Embed(
            title=f"{Z_HAPPY} {member.display_name}'s Profile",
            description=(
                f"**Level:** `{lvl}`\n"
                f"**XP:** `{xp}`  •  **Next:** `{into}/{need}`  (**{pct}%**)\n"
                f"```\n{bar}\n```"
            ),
            color=COLOR,
        )
        # Avatar as thumbnail
        try:
            e.set_thumbnail(url=member.display_avatar.url)
        except Exception:
            pass

        # Stats fields
        e.add_field(name="Messages", value=f"`{msgs}`", inline=True)
        e.add_field(name="Translations", value=f"`{trans}`", inline=True)

        # Voice time
        hours = vsec // 3600
        mins = (vsec % 3600) // 60
        e.add_field(name="Voice Time", value=f"`{hours}h {mins}m`", inline=True)

        # Footer (text only; custom emojis don't render here reliably)
        e.set_footer(text=footer_text())

        await interaction.response.send_message(embed=e, ephemeral=False)

    # Optional: lightweight listener to grant message XP (if you don't already do this elsewhere)
    # Comment out if you’ve implemented message XP in another cog.
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        # Tiny anti-spam: ignore very short messages
        if len(message.content.strip()) < 2:
            return
        try:
            # Grant a small amount of XP per message (tune in utils/config if you prefer)
            await database.add_message_xp(message.guild.id, message.author.id, delta_xp=3)
            # If you want role updates, dispatch an event that your role manager can listen for:
            self.bot.dispatch("xp_gain", message.guild.id, message.author.id)
        except Exception:
            # Silent fail—no log spam for normal message flow
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(XpSystem(bot))
