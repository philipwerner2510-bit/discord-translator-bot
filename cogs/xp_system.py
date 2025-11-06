# cogs/xp_system.py
import math
import discord
from discord.ext import commands
from discord import app_commands

from utils.brand import COLOR, FOOTER, Z1, Z2, Z3   # Z1..Z3 are your Zephyra #1/#2/#3 emojis
from utils import database

# -------- level math --------
def xp_for_level(level: int) -> int:
    # Smooth early game, scales gently.
    # L(n) = 100 + 20*(n-1) + 5*(n-1)^2  (total needed to advance from level n to n+1)
    if level < 0:
        level = 0
    return 100 + 20 * (level) + 5 * (level**2)

def level_from_xp(total_xp: int) -> tuple[int, int, int]:
    """
    Returns (level, remainder_into_level, needed_for_next)
    """
    lvl = 0
    xp = max(0, int(total_xp))
    while True:
        need = xp_for_level(lvl)
        if xp < need:
            return (lvl, xp, need)
        xp -= need
        lvl += 1

# -------- tilted bar renderer (compact, mobile-friendly) --------
def tilted_bar(current: int, needed: int, top=14, bottom=10) -> str:
    """
    Two-row bar, bottom row shorter & indented to look tilted.
    Uses ▰ (filled) / ▱ (empty). Keeps width tight for phones.
    """
    current = max(0, current)
    needed = max(1, needed)
    ratio = min(1.0, current / needed)

    def row(width: int) -> str:
        filled = round(width * ratio)
        empty = max(0, width - filled)
        return "▰" * filled + "▱" * empty

    # slight indent on top row to create the tilt illusion
    top_row = " " + row(top)
    bottom_row = row(bottom)
    return f"`{top_row}`\n`{bottom_row}`"

# --------- Cog ---------
class XpSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ------- /profile -------
    @app_commands.command(name="profile", description="Show your Zephyra XP profile.")
    @app_commands.describe(member="Show another user's profile")
    async def xp_profile(self, interaction: discord.Interaction, member: discord.Member | None = None):
        member = member or interaction.user
        gid = interaction.guild.id

        # read stats
        total_xp, msgs, trans, vsec = await database.get_total_xp(gid, member.id)
        lvl, into, need = level_from_xp(total_xp)

        # embed
        e = discord.Embed(title=f"{member.display_name}'s Profile", color=COLOR)
        e.set_thumbnail(url=member.display_avatar.replace(format="png", size=128).url)

        # header line
        pct = int((into / need) * 100) if need else 100
        e.add_field(name="Level", value=f"**{lvl}**", inline=True)
        e.add_field(name="XP", value=f"**{total_xp}**", inline=True)
        e.add_field(name="Next", value=f"**{into}/{need} ({pct}%)**", inline=True)

        # tilted progress bar
        e.add_field(name="\u200b", value=tilted_bar(into, need), inline=False)

        # compact stats line (integrated style)
        e.add_field(
            name="Stats",
            value=f"**Messages:** {msgs} • **Translations:** {trans} • **Voice:** {vsec // 3600}h {(vsec % 3600) // 60}m",
            inline=False,
        )

        e.set_footer(text=FOOTER)
        await interaction.response.send_message(embed=e)

    # ------- /leaderboard -------
    @app_commands.command(name="leaderboard", description="Server XP leaderboard.")
    async def xp_leaderboard(self, interaction: discord.Interaction):
        gid = interaction.guild.id
        rows = await database.get_top(guild_id=gid, limit=10)

        if not rows:
            return await interaction.response.send_message("No XP yet. Start chatting and translating!", ephemeral=True)

        # format with Zephyra 1/2/3 emotes for the podium
        lines = []
        podium = [str(Z1), str(Z2), str(Z3)]
        for idx, (uid, xp, msgs, trans, vsec) in enumerate(rows, start=1):
            u = interaction.guild.get_member(uid) or await self.bot.fetch_user(uid)
            name = u.display_name if hasattr(u, "display_name") else u.name
            medal = podium[idx - 1] if idx <= 3 else f"**#{idx}**"
            lines.append(
                f"{medal}  **{name}** — XP: **{xp}** · Msg: {msgs} · Tr: {trans} · Voice: {vsec//3600}h"
            )

        e = discord.Embed(title="Leaderboard", description="\n".join(lines), color=COLOR)
        e.set_footer(text=FOOTER)
        await interaction.response.send_message(embed=e)

async def setup(bot: commands.Bot):
    await bot.add_cog(XpSystem(bot))
