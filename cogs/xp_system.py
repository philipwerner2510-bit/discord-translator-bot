# cogs/xp_system.py
# Simple XP system: message XP, /profile & /leaderboard

from __future__ import annotations

from typing import Optional
import discord
from discord.ext import commands
from discord import app_commands

from utils import database
from utils.brand import COLOR, footer_text, NAME

LEADERBOARD_PAGE = 10  # entries per page
XP_PER_MESSAGE = 1     # xp gain per non-bot message


class XPCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --------------------------
    # Passive XP: messages
    # --------------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # ignore bot + DMs
        if message.author.bot or not message.guild:
            return

        try:
            await database.add_xp(
                guild_id=message.guild.id,
                user_id=message.author.id,
                amount=XP_PER_MESSAGE,
                msg_inc=1,
            )
        except Exception as e:
            # stay silent; XP is best-effort
            print(f"[xp] on_message failed in guild {message.guild.id}: {e}")

    # --------------------------
    # /profile
    # --------------------------
    @app_commands.command(name="profile", description="Show your XP profile.")
    async def xp_profile(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            await interaction.followup.send("This command can only be used in a server.", ephemeral=True)
            return

        member = user or interaction.user
        gid = interaction.guild.id

        xp, msgs, trans, vsec = await database.get_xp(gid, member.id)

        e = discord.Embed(
            title=f"{NAME} • Profile",
            color=COLOR,
        )
        e.set_author(name=str(member), icon_url=member.display_avatar.url if member.display_avatar else discord.Embed.Empty)
        e.add_field(name="XP", value=f"{xp}", inline=True)
        e.add_field(name="Messages", value=f"{msgs}", inline=True)
        e.add_field(name="Translations", value=f"{trans}", inline=True)
        e.add_field(name="Voice (sec)", value=f"{vsec}", inline=True)
        e.set_footer(text=footer_text())

        await interaction.followup.send(embed=e, ephemeral=True)

    # --------------------------
    # /leaderboard
    # --------------------------
    @app_commands.command(name="leaderboard", description="Show the XP leaderboard for this server.")
    @app_commands.describe(page="Page number (starts at 1)")
    async def xp_leaderboard(self, interaction: discord.Interaction, page: Optional[int] = 1):
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            await interaction.followup.send("This command can only be used in a server.", ephemeral=True)
            return

        page = max(1, page or 1)
        offset = (page - 1) * LEADERBOARD_PAGE
        rows = await database.get_xp_leaderboard(interaction.guild.id, LEADERBOARD_PAGE, offset)

        if not rows:
            await interaction.followup.send(f"No XP data yet for page {page}.", ephemeral=True)
            return

        lines = []
        start_rank = offset + 1
        for i, (user_id, xp, msgs, trans, vsec) in enumerate(rows, start=start_rank):
            user = interaction.guild.get_member(user_id) or self.bot.get_user(user_id)
            name = user.mention if isinstance(user, discord.Member) else (user.mention if user else f"<@{user_id}>")
            lines.append(f"**{i}.** {name} — **{xp} XP** · {msgs} msgs · {trans} trans")

        e = discord.Embed(
            title=f"{NAME} • Leaderboard (Page {page})",
            description="\n".join(lines),
            color=COLOR,
        )
        e.set_footer(text=footer_text())
        await interaction.followup.send(embed=e, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(XPCog(bot))
