# cogs/xp_system.py
import math
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
from utils import database
from utils.brand import COLOR, NAME
from utils.config import LEADERBOARD_PAGE

class XpSystem(commands.Cog, name="XP"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # /profile
    @app_commands.command(name="profile", description="Show your (or another member's) XP profile.")
    @app_commands.describe(member="Whose profile to view (defaults to you)")
    async def xp_profile(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        await interaction.response.defer(ephemeral=False)
        member = member or interaction.user
        gid = interaction.guild_id
        xp, msgs, trans, vsec = await database.get_xp(gid, member.id)

        e = discord.Embed(
            title=f"{member.display_name}'s Zephyra Profile",
            color=COLOR,
            description=f"**XP:** {xp}\n**Messages:** {msgs}\n**Translations:** {trans}\n**Voice:** {vsec//60} min ({vsec}s)"
        )
        e.set_thumbnail(url=member.display_avatar.url)
        e.set_footer(text=f"{NAME} — XP Profile")
        await interaction.followup.send(embed=e)

    # /leaderboard
    @app_commands.command(name="leaderboard", description="Show this server's XP leaderboard.")
    @app_commands.describe(page="Page number (10 per page)")
    async def xp_leaderboard(self, interaction: discord.Interaction, page: Optional[int] = 1):
        await interaction.response.defer()
        page = max(1, page or 1)
        offset = (page - 1) * LEADERBOARD_PAGE
        rows = await database.get_xp_leaderboard(interaction.guild_id, LEADERBOARD_PAGE, offset)

        if not rows:
            await interaction.followup.send("No XP tracked yet on this server.")
            return

        lines = []
        rank_start = offset + 1
        for idx, (user_id, xp, msgs, trans, vsec) in enumerate(rows, start=0):
            member = interaction.guild.get_member(user_id)
            name = member.display_name if member else f"<@{user_id}>"
            lines.append(
                f"**{rank_start+idx}.** {name} — XP **{xp}** · Msg **{msgs}** · Tr **{trans}** · Voice **{vsec//60}m**"
            )

        e = discord.Embed(
            title=f"{interaction.guild.name} — XP Leaderboard",
            description="\n".join(lines),
            color=COLOR,
        )
        e.set_footer(text=f"{NAME} — Page {page}")
        await interaction.followup.send(embed=e)

async def setup(bot: commands.Bot):
    await bot.add_cog(XpSystem(bot))
