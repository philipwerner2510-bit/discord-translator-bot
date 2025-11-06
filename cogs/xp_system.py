# cogs/xp_system.py
import discord
from discord.ext import commands
from discord import app_commands

from utils.brand import COLOR, NAME
from utils import database

LEVEL_STEP = 100
BAR_CELLS  = 17
BAR_FILLED = "▰"
BAR_EMPTY  = "▱"

EMO_R1 = "<:Zephyra_emote_1:1436100371058790431>"
EMO_R2 = "<:Zephyra_emote_2:1436100410292043866>"
EMO_R3 = "<:Zephyra_emote_3:1436100442571669695>"

PAGE_SIZE = 10

def level_stats(total_xp: int):
    total_xp = max(0, int(total_xp))
    level = total_xp // LEVEL_STEP
    cur   = total_xp % LEVEL_STEP
    nxt   = LEVEL_STEP
    pct   = 0 if nxt == 0 else int((cur / nxt) * 100)
    return level, cur, nxt, pct

def bar_line(cur: int, nxt: int) -> str:
    if nxt <= 0:
        return BAR_EMPTY * BAR_CELLS
    filled = max(0, min(BAR_CELLS, int(round((cur / nxt) * BAR_CELLS))))
    return (BAR_FILLED * filled) + (BAR_EMPTY * (BAR_CELLS - filled))

def voice_fmt(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return f"{h}h {m}m"

def rank_badge(rank: int) -> str:
    if rank == 1: return EMO_R1
    if rank == 2: return EMO_R2
    if rank == 3: return EMO_R3
    return f"#{rank}"

FOOTER = f"{NAME} — Developed by Polarix1954"

class XpSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_xp_gain")
    async def _on_xp_gain(self, guild_id: int, user_id: int):
        # placeholder hook for future live-updates
        return

    # ---------- /profile ----------
    @app_commands.guild_only()
    @app_commands.command(name="profile", description="Show your Zephyra XP profile.")
    @app_commands.describe(member="Show another member's profile")
    async def profile(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        gid = interaction.guild.id

        total_xp, messages, translations, voice_seconds = await database.get_xp(gid, member.id)
        level, cur, nxt, pct = level_stats(total_xp)

        e = discord.Embed(color=COLOR, title=f"{member.display_name}'s Profile")
        e.add_field(name="Level", value=f"**{level}**", inline=False)
        e.add_field(name="XP", value=f"**{cur}** • Next: **{cur}/{nxt} ({pct}%)**", inline=False)
        e.add_field(name="\u200b", value=f"`{bar_line(cur, nxt)}`", inline=False)
        e.add_field(name="Messages", value=f"**{messages}**", inline=True)
        e.add_field(name="Translations", value=f"**{translations}**", inline=True)
        e.add_field(name="Voice Time", value=f"**{voice_fmt(voice_seconds)}**", inline=True)

        try:
            e.set_thumbnail(url=member.display_avatar.replace(format="png", size=256).url)
        except Exception:
            e.set_thumbnail(url=member.display_avatar.url)

        e.set_footer(text=FOOTER)
        await interaction.response.send_message(embed=e)

    # ---------- /leaderboard ----------
    @app_commands.guild_only()
    @app_commands.command(name="leaderboard", description="Show the XP leaderboard for this server.")
    @app_commands.describe(page="Page number (starting at 1)")
    async def leaderboard(self, interaction: discord.Interaction, page: int = 1):
        gid = interaction.guild.id
        page = max(1, int(page))
        offset = (page - 1) * PAGE_SIZE

        rows = await database.get_xp_leaderboard(gid, limit=PAGE_SIZE, offset=offset)
        if not rows:
            e = discord.Embed(color=COLOR, title="Leaderboard")
            e.description = "No XP data yet."
            e.set_footer(text=FOOTER)
            return await interaction.response.send_message(embed=e, ephemeral=True)

        lines = []
        start_rank = offset + 1
        for idx, (user_id, xp, msgs, trans, vsec) in enumerate(rows, start=start_rank):
            badge = rank_badge(idx) if idx <= 3 else f"#{idx}"
            member = interaction.guild.get_member(user_id)
            name = member.display_name if member else f"<@{user_id}>"
            lvl, cur, nxt, pct = level_stats(xp)
            lines.append(f"{badge} **{name}** — L{lvl} • {xp} XP • msgs: {msgs} • trans: {trans} • voice: {voice_fmt(vsec)}")

        e = discord.Embed(color=COLOR, title=f"Leaderboard — Page {page}")
        e.description = "\n".join(lines)
        e.set_footer(text=FOOTER)
        await interaction.response.send_message(embed=e)

async def setup(bot):
    await bot.add_cog(XpSystem(bot))
