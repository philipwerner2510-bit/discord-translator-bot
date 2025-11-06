# cogs/xp_system.py
# Profile & Leaderboard with level system, avatar & medals.
import math
import discord
from discord.ext import commands
from discord import app_commands

from utils.brand import (
    COLOR, ACCENT, PROFILE_TITLE, LEADERBOARD_TITLE,
    MEDAL_1, MEDAL_2, MEDAL_3, medal_for_rank, footer
)
from utils import database

# Tunable XP values (keep aligned with your other cogs)
XP_PER_MESSAGE = 5

def progress_bar(curr: int, need: int, width: int = 10) -> str:
    if need <= 0:
        return "■" * width
    ratio = max(0.0, min(1.0, curr / need))
    filled = int(round(ratio * width))
    return "■" * filled + "□" * (width - filled)

class XpSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Optional central message XP hook (enable if you want this cog to give message XP)
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        # award small XP for any non-empty content
        if message.content and message.content.strip():
            try:
                await database.add_message_xp(message.guild.id, message.author.id, XP_PER_MESSAGE)
                # Let others (roles, etc.) react if you want: self.bot.dispatch("xp_gain", ...)
            except Exception:
                pass

    # /profile
    @app_commands.command(name="profile", description="Show your Zephyra profile & level.")
    @app_commands.describe(member="User to inspect (default: you)")
    async def xp_profile(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        gid = interaction.guild.id

        xp, msgs, trans, vsec = await database.get_xp(gid, member.id)
        lvl, into, need = database.level_from_xp(xp)
        bar = progress_bar(into, need, width=10)

        e = discord.Embed(
            title=f"{PROFILE_TITLE}",
            description=(
                f"**Level {lvl}**\n"
                f"XP: **{xp:,}**\n"
                f"`{bar}`  **{into}/{need}** to next level\n\n"
                f"• Messages: **{msgs:,}**\n"
                f"• Translations: **{trans:,}**\n"
                f"• Voice: **{vsec:,}s**"
            ),
            color=COLOR
        )
        # user avatar
        if member.display_avatar:
            e.set_thumbnail(url=member.display_avatar.url)
        e.set_footer(text=footer())
        await interaction.response.send_message(embed=e)

    # /leaderboard
    @app_commands.command(name="leaderboard", description="Top users by XP in this server.")
    @app_commands.describe(page="Page number (starts at 1)")
    async def xp_leaderboard(self, interaction: discord.Interaction, page: int = 1):
        gid = interaction.guild.id
        page = max(1, page)
        limit = database.LEADERBOARD_PAGE
        offset = (page - 1) * limit

        rows = await database.get_xp_leaderboard(gid, limit=limit, offset=offset)

        if not rows:
            return await interaction.response.send_message(
                embed=discord.Embed(description="No data yet. Start chatting!", color=COLOR).set_footer(text=footer())
            )

        lines = []
        for i, (uid, xp, msgs, trans, vsec) in enumerate(rows, start=offset + 1):
            lvl, _, _ = database.level_from_xp(int(xp))
            try:
                user = interaction.guild.get_member(int(uid)) or await interaction.guild.fetch_member(int(uid))
                name = user.display_name
            except Exception:
                name = f"User {uid}"

            medal = medal_for_rank(i) if i <= 3 else f"#{i}"
            lines.append(f"{medal} **{name}** — LVL **{lvl}** · XP **{int(xp):,}**")

        e = discord.Embed(
            title=LEADERBOARD_TITLE,
            description="\n".join(lines),
            color=COLOR
        )
        e.set_footer(text=f"{footer()} • Page {page}")
        await interaction.response.send_message(embed=e)

async def setup(bot):
    await bot.add_cog(XpSystem(bot))
