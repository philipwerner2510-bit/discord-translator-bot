# cogs/ops_commands.py
import time
import discord
from discord.ext import commands
from discord import app_commands
from utils.brand import COLOR, footer

def _footer_text() -> str:
    try:
        return footer()
    except TypeError:
        return str(footer)

class Ops(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._boot = time.perf_counter()

    # create a slash-group to avoid global name collisions
    ops = app_commands.Group(name="ops", description="Operational tools")

    @ops.command(name="ping", description="Latency & shard stats.")
    async def ops_ping(self, interaction: discord.Interaction):
        hb = round(self.bot.latency * 1000)
        up = time.perf_counter() - self._boot
        e = (discord.Embed(title="Pong!", color=COLOR)
             .add_field(name="WebSocket", value=f"{hb} ms")
             .add_field(name="Uptime", value=f"{int(up)}s")
             .set_footer(text=_footer_text()))
        await interaction.response.send_message(embed=e, ephemeral=True)

    @ops.command(name="reload", description="Owner: reload a cog (e.g. cogs.translate).")
    @app_commands.describe(cog="Module path, e.g. cogs.translate")
    async def ops_reload(self, interaction: discord.Interaction, cog: str):
        if interaction.user.id != interaction.client.owner_id:
            return await interaction.response.send_message("Owner only.", ephemeral=True)
        try:
            await interaction.client.reload_extension(cog)
            e = discord.Embed(description=f"✅ Reloaded `{cog}`", color=COLOR)
        except Exception as exc:
            e = discord.Embed(description=f"❌ Reload failed for `{cog}`:\n`{exc}`", color=COLOR)
        e.set_footer(text=_footer_text())
        await interaction.response.send_message(embed=e, ephemeral=True)

    @ops.command(name="selftest", description="Run a quick health check.")
    async def ops_selftest(self, interaction: discord.Interaction):
        ok = ["Slash tree OK", "Embeds OK", "Permissions OK"]
        e = (discord.Embed(title="Self-test", description="• " + "\n• ".join(ok), color=COLOR)
             .set_footer(text=_footer_text()))
        await interaction.response.send_message(embed=e, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Ops(bot))
