# cogs/owner_commands.py
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from utils.brand import ACCENT, NAME, footer_text

OWNER_ID = 762267166031609858  # Polarix1954


def is_owner():
    async def predicate(interaction: discord.Interaction) -> bool:
        return interaction.user.id == OWNER_ID
    return app_commands.check(predicate)


class Owner(commands.Cog):
    """Owner-only utilities (under /owner)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    owner = app_commands.Group(
        name="owner",
        description="Owner-only utilities",
        guild_only=False,
    )

    @owner.command(name="guilds", description="List the guilds this bot is in.")
    @is_owner()
    async def guilds(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        guilds = sorted(self.bot.guilds, key=lambda g: g.member_count or 0, reverse=True)
        lines = [f"• **{g.name}** — {g.member_count or 0} members (ID `{g.id}`)" for g in guilds[:25]] or ["No guilds."]
        embed = (
            discord.Embed(title="Owner • Guilds", description="\n".join(lines), color=ACCENT)
            .set_author(name=NAME)
            .set_footer(text=footer_text())
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    # Leave public /stats in analytics; owner view is namespaced:
    @owner.command(name="ownerstats", description="Bot stats (owner view).")
    @is_owner()
    async def ownerstats(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        gcount = len(self.bot.guilds)
        ucount = sum(g.member_count or 0 for g in self.bot.guilds)
        embed = (
            discord.Embed(
                title="Owner • Stats",
                description=f"Servers: **{gcount}**\nUsers (approx): **{ucount:,}**",
                color=ACCENT,
            )
            .set_author(name=NAME)
            .set_footer(text=footer_text())
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @owner.command(name="reload", description="Reload bot extensions / cogs.")
    @is_owner()
    async def reload(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        failures = []
        reloaded = []
        for ext in list(self.bot.extensions.keys()):
            try:
                await self.bot.reload_extension(ext)
                reloaded.append(ext)
            except Exception:
                failures.append(ext)

        desc = "🔄 Reload complete.\n"
        if failures:
            desc += f"❌ Failed: {', '.join(failures)}"
        else:
            desc += "✅ All cogs reloaded"

        await interaction.followup.send(desc, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Owner(bot))
    # Guard to avoid CommandAlreadyRegistered on reload:
    if not any(cmd.name == "owner" for cmd in bot.tree.get_commands()):
        bot.tree.add_command(Owner.owner)