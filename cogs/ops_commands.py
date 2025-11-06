# cogs/ops_commands.py
import time
import discord
from discord.ext import commands
from discord import app_commands

from utils.brand import COLOR, footer  # do NOT touch brand.py

def _footer_text() -> str:
    # brand.footer might be a function or a string — normalize to string.
    try:
        ft = footer()  # callable?
    except TypeError:
        ft = footer  # already a string
    return str(ft)

class Ops(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._boot = time.perf_counter()

    @app_commands.command(name="ping", description="Latency & shard stats.")
    async def ping(self, interaction: discord.Interaction):
        hb = round(self.bot.latency * 1000)
        up = time.perf_counter() - self._boot
        e = (discord.Embed(title="Pong!", color=COLOR)
             .add_field(name="WebSocket", value=f"{hb} ms")
             .add_field(name="Uptime", value=f"{int(up)}s")
             .set_footer(text=_footer_text()))
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="reload", description="Owner: reload a cog.")
    @app_commands.describe(cog="cogs.module_name (e.g., cogs.translate)")
    async def reload(self, interaction: discord.Interaction, cog: str):
        if interaction.user.id != interaction.client.owner_id:
            return await interaction.response.send_message("Owner only.", ephemeral=True)

        try:
            await interaction.client.reload_extension(cog)
            e = discord.Embed(description=f"✅ Reloaded `{cog}`", color=COLOR)
        except Exception as e1:
            e = discord.Embed(description=f"❌ Reload failed for `{cog}`:\n`{e1}`", color=COLOR)
        e.set_footer(text=_footer_text())
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="selftest", description="Run a quick health check.")
    async def selftest(self, interaction: discord.Interaction):
        ok = ["Slash tree OK", "Embeds OK", "Permissions OK"]
        e = (discord.Embed(title="Self-test", description="• " + "\n• ".join(ok), color=COLOR)
             .set_footer(text=_footer_text()))
        await interaction.response.send_message(embed=e, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Ops(bot))
