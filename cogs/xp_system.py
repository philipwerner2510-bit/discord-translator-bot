# cogs/xp_system.py
from __future__ import annotations

import math
import discord
from discord.ext import commands
from discord import app_commands

from utils.brand import COLOR, footer  # no other brand pulls
from utils import database
from utils.roles import role_ladder

# Leaderboard rank emotes — embed here so we don't rely on brand.py
Z_NUM_1 = "<:Zephyra_emote_1:1436100371058790431>"
Z_NUM_2 = "<:Zephyra_emote_2:1436100410292043866>"
Z_NUM_3 = "<:Zephyra_emote_3:1436100442571669695>"

# --- leveling rules ---
LEVEL_CAP = 100

def xp_for_level(level: int) -> int:
    """Total XP required to REACH `level`. L1=0, grows quadratic-ish."""
    if level <= 1:
        return 0
    # Smooth quadratic curve: ~ 50 * n^2
    return 50 * (level - 1) * (level - 1)

def level_from_xp(total_xp: int) -> int:
    """Inverse of xp_for_level with clamp to LEVEL_CAP."""
    # Solve 50*(l-1)^2 <= xp
    l = int(math.sqrt(max(0, total_xp) / 50.0) + 1)
    return max(1, min(LEVEL_CAP, l))

def progress_bar(progress: float, width: int = 16) -> str:
    """Discord-friendly bar using ▰ (filled) and ▱ (empty)."""
    progress = max(0.0, min(1.0, progress))
    filled = int(round(progress * width))
    return "▰" * filled + "▱" * (width - filled)

def _footer_text() -> str:
    try:
        return footer()
    except TypeError:
        return str(footer)

class XPSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ----- helpers used by other cogs -----
    async def _on_text_activity(self, guild_id: int, user_id: int):
        # call this from your message/translate flows if you want passive gain
        await database.add_message_xp(guild_id, user_id, 3)  # small passive
        # role sync can be dispatched by events cog if desired

    # ----- /profile -----
    @app_commands.command(name="profile", description="Show your Zephyra level profile.")
    @app_commands.describe(member="See another member's profile.")
    async def xp_profile(self, interaction: discord.Interaction, member: discord.Member | None = None):
        member = member or interaction.user
        gid = interaction.guild.id

        xp, msgs, trans, vsec = await database.get_xp(gid, member.id)
        level = level_from_xp(xp)
        nxt = min(LEVEL_CAP, level + 1)
        cur_req = xp_for_level(level)
        nxt_req = xp_for_level(nxt)
        span = max(1, nxt_req - cur_req)
        pct = (xp - cur_req) / span if span else 1.0

        bar = progress_bar(pct, width=16)  # exact bar you asked for

        e = (discord.Embed(title=f"{member.display_name}", color=COLOR)
             .add_field(name="Level", value=f"{level}/{LEVEL_CAP}")
             .add_field(name="XP", value=f"{xp:,} / {nxt_req:,}")
             .add_field(name="Progress", value=bar, inline=False)
             .add_field(name="Messages", value=str(msgs))
             .add_field(name="Translations", value=str(trans))
             .add_field(name="Voice (s)", value=str(vsec))
             .set_thumbnail(url=member.display_avatar.url)
             .set_footer(text=_footer_text()))
        await interaction.response.send_message(embed=e)

    # ----- /leaderboard -----
    @app_commands.command(name="leaderboard", description="Top XP on this server.")
    async def xp_leaderboard(self, interaction: discord.Interaction):
        gid = interaction.guild.id
        rows = await database.get_xp_leaderboard(gid, limit=10, offset=0)

        if not rows:
            e = discord.Embed(description="No XP yet. Start chatting or translating!", color=COLOR)
            e.set_footer(text=_footer_text())
            return await interaction.response.send_message(embed=e, ephemeral=True)

        lines = []
        for i, (uid, xp, msgs, trans, vsec) in enumerate(rows, start=1):
            level = level_from_xp(xp)
            if i == 1:
                rank = Z_NUM_1
            elif i == 2:
                rank = Z_NUM_2
            elif i == 3:
                rank = Z_NUM_3
            else:
                rank = f"#{i}"

            member = interaction.guild.get_member(uid)
            name = member.display_name if member else f"User {uid}"
            lines.append(f"{rank} **{name}** — L{level} · {xp:,} XP · 🗨️ {msgs} · 🌐 {trans} · 🎙️ {vsec}s")

        e = (discord.Embed(title="Leaderboard", description="\n".join(lines), color=COLOR)
             .set_footer(text=_footer_text()))
        await interaction.response.send_message(embed=e)

async def setup(bot: commands.Bot):
    await bot.add_cog(XPSystem(bot))
