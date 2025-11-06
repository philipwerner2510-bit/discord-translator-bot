# cogs/ops_commands.py
import os
import time
import importlib
import discord
from discord.ext import commands
from discord import app_commands

from utils.brand import COLOR, footer_text, NAME


def _owner_check(bot: commands.Bot):
    owner_ids = set()
    if getattr(bot, "owner_ids", None):
        owner_ids |= set(bot.owner_ids)
    env_ids = os.getenv("OWNER_IDS", "")
    for s in env_ids.split(","):
        s = s.strip()
        if s.isdigit():
            owner_ids.add(int(s))
    if getattr(bot, "owner_id", None):
        owner_ids.add(bot.owner_id)

    def check(interaction: discord.Interaction):
        return interaction.user.id in owner_ids
    return app_commands.check(check)


class OpsCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Latency & heartbeat.")
    async def ping(self, interaction: discord.Interaction):
        ws = self.bot.latency * 1000.0
        e = discord.Embed(
            title=f"{NAME} — Ping",
            description=f"WebSocket: **{ws:.0f}ms**",
            color=COLOR
        ).set_footer(text=footer_text)
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="reload", description="Reload cogs (owner only).")
    @_owner_check.__func__(None)  # type: ignore
    async def reload(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        reloaded = []
        failed = []
        for ext in list(self.bot.extensions.keys()):
            try:
                await self.bot.reload_extension(ext)
                reloaded.append(ext)
            except Exception as e:
                failed.append((ext, str(e)))
        desc = f"**Reloaded:**\n" + ("\n".join(reloaded) if reloaded else "(none)")
        if failed:
            desc += "\n\n**Failed:**\n" + "\n".join(f"{n} — `{err}`" for n, err in failed)
        e = discord.Embed(title=f"{NAME} — Reload", description=desc, color=COLOR).set_footer(text=footer_text)
        await interaction.followup.send(embed=e, ephemeral=True)

    @app_commands.command(name="selftest", description="Basic self test.")
    async def selftest(self, interaction: discord.Interaction):
        e = discord.Embed(
            title=f"{NAME} — Self Test",
            description="OK.",
            color=COLOR
        ).set_footer(text=footer_text)
        await interaction.response.send_message(embed=e, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(OpsCommands(bot))
