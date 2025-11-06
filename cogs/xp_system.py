# cogs/xp_system.py
import math
import asyncio
from typing import Optional, List, Tuple

import discord
from discord.ext import commands
from discord import app_commands

from utils.brand import COLOR, footer  # ← use footer() (function), not FOOTER (const)
from utils import database

# Try to import the custom rank emotes if you kept them in brand.py.
# If they don't exist there, we'll fall back to plain text.
try:
    from utils.brand import Z1, Z2, Z3  # optional
except Exception:
    Z1 = "🥇"
    Z2 = "🥈"
    Z3 = "🥉"

# ---------- Level math ----------
BASE_REQ = 100  # XP needed for level 1
SCALE = 1.00    # linear for now (you can curve this later)

def xp_for_level(level: int) -> int:
    """Total XP required to REACH 'level' (level 0 => 0)."""
    return int(BASE_REQ * SCALE * level)

def next_level_target(level: int) -> int:
    """XP required to go from level -> level+1."""
    return xp_for_level(level + 1) - xp_for_level(level)

def level_from_xp(total_xp: int) -> int:
    """Inverse of xp_for_level (for this linear model)."""
    if total_xp <= 0:
        return 0
    # linear: level = total_xp / BASE_REQ (floored)
    return max(0, total_xp // int(BASE_REQ * SCALE))

def progress_in_level(total_xp: int) -> tuple[int, int, float]:
    """Returns (cur, need, pct 0..1) for the current level."""
    lvl = level_from_xp(total_xp)
    have = total_xp - xp_for_level(lvl)
    need = next_level_target(lvl)
    pct = 0.0 if need <= 0 else have / need
    return have, need, max(0.0, min(1.0, pct))

# ---------- Pretty bar (tilted look) ----------
# Mobile-friendly width: 12 cells total with a slanted start cap.
FULL_CELL = "▮"
EMPTY_CELL = "▯"
START_TILT = "◢"   # gives that slightly “turned” first cell
END_TILT = "◣"

def progress_bar(pct: float, cells: int = 12) -> str:
    pct = max(0.0, min(1.0, pct))
    filled = int(round(pct * cells))
    filled = max(0, min(cells, filled))
    # Build body without caps first
    body = FULL_CELL * filled + EMPTY_CELL * (cells - filled)
    if cells >= 2:
        body = START_TILT + body[1:-1] + END_TILT
    return body

# ---------- Cog ----------
class XPSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Lightweight listener: award message XP
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        # small XP per message; adjust if you want
        try:
            await database.add_message_xp(message.guild.id, message.author.id, 2)
        except Exception:
            pass

    # also listen to the custom event fired by translate cog
    @commands.Cog.listener()
    async def on_xp_gain(self, guild_id: int, user_id: int):
        # currently unused, but here for future role gating etc.
        return

    # /profile
    @app_commands.command(name="profile", description="Show your Zephyra XP profile.")
    @app_commands.describe(member="Optionally view another user's profile")
    async def xp_profile(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        member = member or interaction.user
        gid = interaction.guild.id if interaction.guild else 0

        total_xp, msgs, trans, vsec = await database.get_xp(gid, member.id)
        lvl = level_from_xp(total_xp)
        cur, need, pct = progress_in_level(total_xp)
        bar = progress_bar(pct)

        e = discord.Embed(
            title=f"{member.display_name}'s Profile",
            color=COLOR
        )
        # avatar
        if member.display_avatar:
            e.set_thumbnail(url=member.display_avatar.replace(static_format="png", size=256).url)

        # header line
        e.add_field(name="Level", value=f"**{lvl}**", inline=True)
        e.add_field(name="XP", value=f"**{total_xp}**", inline=True)
        e.add_field(name="Next", value=f"**{cur}/{need} ({int(pct*100)}%)**", inline=True)

        # tilted progress bar
        e.add_field(name="\u200b", value=f"`{bar}`  **{cur}/{need}** to next level", inline=False)

        # stats line
        e.add_field(name="Messages", value=f"**{msgs}**", inline=True)
        e.add_field(name="Translations", value=f"**{trans}**", inline=True)
        # voice seconds → pretty time
        hours = vsec // 3600
        mins = (vsec % 3600) // 60
        e.add_field(name="Voice Time", value=f"**{hours}h {mins}m**", inline=True)

        e.set_footer(text=footer())  # ← use your function from brand.py
        await interaction.response.send_message(embed=e)

    # /leaderboard
    @app_commands.command(name="leaderboard", description="Show the server XP leaderboard.")
    @app_commands.describe(page="Which page (10 per page)")
    async def leaderboard(self, interaction: discord.Interaction, page: Optional[int] = 1):
        if page is None or page < 1:
            page = 1
        gid = interaction.guild.id if interaction.guild else 0
        limit = database.LEADERBOARD_PAGE
        offset = (page - 1) * limit

        rows = await database.get_xp_leaderboard(gid, limit=limit, offset=offset)

        if not rows:
            e = discord.Embed(description="No XP data yet.", color=COLOR)
            e.set_footer(text=footer())
            return await interaction.response.send_message(embed=e, ephemeral=True)

        lines = []
        for idx, (uid, xp, msgs, trans, vsec) in enumerate(rows, start=1 + offset):
            # resolve member name if possible
            member = interaction.guild.get_member(int(uid))
            name = member.display_name if member else f"User {uid}"

            # ranks 1–3 with Zephyra podium emotes (or emoji fallback)
            if idx == 1:
                rank = f"{Z1}"
            elif idx == 2:
                rank = f"{Z2}"
            elif idx == 3:
                rank = f"{Z3}"
            else:
                rank = f"**#{idx}**"

            lvl = level_from_xp(int(xp))
            lines.append(
                f"{rank}  **{name}** — LVL **{lvl}** · XP **{xp}** · msgs **{msgs}** · trans **{trans}**"
            )

        e = discord.Embed(title="XP Leaderboard", description="\n".join(lines), color=COLOR)
        e.set_footer(text=f"{footer()} • Page {page}")
        await interaction.response.send_message(embed=e)

async def setup(bot: commands.Bot):
    await bot.add_cog(XPSystem(bot))
