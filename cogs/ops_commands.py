# cogs/ops_commands.py
import os
import discord
from discord.ext import commands
from discord import app_commands

from utils.brand import COLOR, footer_text, NAME


def owner_only():
    """Inline owner-only guard (no external module)."""
    def predicate(interaction: discord.Interaction) -> bool:
        bot = interaction.client

        owner_ids = set()
        if getattr(bot, "owner_id", None):
            owner_ids.add(bot.owner_id)
        if getattr(bot, "owner_ids", None):
            owner_ids |= set(bot.owner_ids)

        env_ids = os.getenv("OWNER_IDS", "")
        for token in env_ids.split(","):
            token = token.strip()
            if token.isdigit():
                owner_ids.add(int(token))

        return interaction.user.id in owner_ids
    return app_commands.check(predicate)


class OpsCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Latency & heartbeat.")
    async def ping(self, interaction: discord.Interaction):
        ws = interaction.client.latency * 1000.0
        e = (
            discord.Embed(
                title=f"{NAME} — Ping",
                description=f"WebSocket: **{ws:.0f} ms**",
                color=COLOR,
            ).set_footer(text=footer_text)   # NOTE: footer_text is a STRING
        )
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="reload", description="Reload all loaded cogs (owner only).")
    @owner_only()
    async def reload(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        reloaded, failed = [], []
        for ext in list(self.bot.extensions.keys()):
            try:
                await self.bot.reload_extension(ext)
                reloaded.append(ext)
            except Exception as e:
                failed.append((ext, str(e)))

        desc = ""
        desc += "**Reloaded:**\n" + ("\n".join(reloaded) if reloaded else "(none)")
        if failed:
            desc += "\n\n**Failed:**\n" + "\n".join(f"{n} — `{err}`" for n, err in failed)

        e = discord.Embed(title=f"{NAME} — Reload", description=desc, color=COLOR).set_footer(text=footer_text)
        await interaction.followup.send(embed=e, ephemeral=True)

    @app_commands.command(name="selftest", description="Basic self test.")
    async def selftest(self, interaction: discord.Interaction):
        e = (
            discord.Embed(
                title=f"{NAME} — Self Test",
                description="OK.",
                color=COLOR,
            ).set_footer(text=footer_text)
        )
        await interaction.response.send_message(embed=e, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(OpsCommands(bot))
