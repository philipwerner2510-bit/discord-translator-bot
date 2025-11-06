# cogs/owner_commands.py
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.brand import ACCENT, NAME, FOOTER_DEV


def is_owner():
    async def predicate(interaction: discord.Interaction) -> bool:
        app_info = await interaction.client.application_info()
        return interaction.user.id == app_info.owner.id
    return app_commands.check(predicate)


class Owner(commands.Cog):
    """Owner-only utilities (namespaced under /owner)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    owner = app_commands.Group(
        name="owner",
        description="Owner-only utilities",
        guild_only=False,
    )

    @owner.command(name="guilds", description="List the guilds this bot is in.")
    @is_owner()
    async def owner_guilds(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        guilds = sorted(self.bot.guilds, key=lambda g: g.member_count or 0, reverse=True)
        lines = [f"• **{g.name}** — {g.member_count or 0} members (ID `{g.id}`)" for g in guilds[:25]]
        if not lines:
            lines = ["No guilds found."]

        embed = discord.Embed(
            title="Owner • Guilds",
            description="\n".join(lines),
            color=ACCENT,
        ).set_author(name=NAME)
        embed.set_footer(text=FOOTER_DEV)
        await interaction.followup.send(embed=embed, ephemeral=True)

    # Renamed from /stats to avoid collisions with analytics_commands
    @owner.command(name="owner