# cogs/owner_commands.py
import os
import discord
from discord.ext import commands
from discord import app_commands

from utils.brand import COLOR, footer_text, NAME

def _owner_check(bot: commands.Bot):
    owner_ids = set()
    # Prefer discord.py native owner_ids if set on bot
    if getattr(bot, "owner_ids", None):
        owner_ids |= set(bot.owner_ids)
    # ENV fallback
    env_ids = os.getenv("OWNER_IDS", "")
    for s in env_ids.split(","):
        s = s.strip()
        if s.isdigit():
            owner_ids.add(int(s))
    # single owner id fallback
    if getattr(bot, "owner_id", None):
        owner_ids.add(bot.owner_id)

    def check(interaction: discord.Interaction):
        return interaction.user.id in owner_ids
    return app_commands.check(check)


class OwnerCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    group = app_commands.Group(name="owner", description="Owner commands")

    @group.command(name="guilds", description="List guilds the bot is in.")
    @_owner_check.__func__(None)  # type: ignore
    async def guilds(self, interaction: discord.Interaction):
        lines = []
        total_members = 0
        for g in self.bot.guilds:
            total_members += g.member_count or 0
            lines.append(f"• **{g.name}** (`{g.id}`) — {g.member_count} members")
        desc = "\n".join(lines) if lines else "(no guilds)"
        e = discord.Embed(
            title=f"{NAME} — Guilds",
            description=desc,
            color=COLOR
        ).set_footer(text=footer_text)
        await interaction.response.send_message(embed=e, ephemeral=True)

    @group.command(name="ownerstats", description="Owner stats snapshot.")
    @_owner_check.__func__(None)  # type: ignore
    async def ownerstats(self, interaction: discord.Interaction):
        guilds = len(self.bot.guilds)
        users = sum(g.member_count or 0 for g in self.bot.guilds)
        e = discord.Embed(
            title=f"{NAME} — Owner Stats",
            description=f"**Guilds:** {guilds}\n**Users (approx):** {users}",
            color=COLOR
        ).set_footer(text=footer_text)
        await interaction.response.send_message(embed=e, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(OwnerCommands(bot))
