# cogs/owner_commands.py
import os
import discord
from discord.ext import commands
from discord import app_commands

from utils.brand import COLOR, footer_text, NAME


def _is_owner_interaction(interaction: discord.Interaction) -> bool:
    owner_ids = set()

    # IDs bound to the client (supports multiple owners)
    if getattr(interaction.client, "owner_ids", None):
        owner_ids |= set(interaction.client.owner_ids)
    if getattr(interaction.client, "owner_id", None):
        owner_ids.add(interaction.client.owner_id)

    # Environment fallback
    env_ids = os.getenv("OWNER_IDS", "")
    for token in env_ids.split(","):
        token = token.strip()
        if token.isdigit():
            owner_ids.add(int(token))

    return interaction.user.id in owner_ids


class OwnerCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    owner = app_commands.Group(name="owner", description="Owner commands")

    @owner.command(name="guilds", description="List guilds the bot is in.")
    @app_commands.check(_is_owner_interaction)
    async def guilds(self, interaction: discord.Interaction):
        lines = []
        total_members = 0
        for g in self.bot.guilds:
            total_members += g.member_count or 0
            lines.append(f"• **{g.name}** (`{g.id}`) — {g.member_count} members")

        e = (
            discord.Embed(
                title=f"{NAME} — Guilds",
                description="\n".join(lines) if lines else "(no guilds)",
                color=COLOR,
            )
            .set_footer(text=footer_text)
        )
        await interaction.response.send_message(embed=e, ephemeral=True)

    @owner.command(name="ownerstats", description="Owner stats snapshot.")
    @app_commands.check(_is_owner_interaction)
    async def ownerstats(self, interaction: discord.Interaction):
        guilds = len(self.bot.guilds)
        users = sum(g.member_count or 0 for g in self.bot.guilds)
        e = (
            discord.Embed(
                title=f"{NAME} — Owner Stats",
                description=f"**Guilds:** {guilds}\n**Users (approx):** {users}",
                color=COLOR,
            )
            .set_footer(text=footer_text)
        )
        await interaction.response.send_message(embed=e, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(OwnerCommands(bot))
