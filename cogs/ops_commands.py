# cogs/ops_commands.py
import os
import time
import discord
from discord.ext import commands
from discord import app_commands
from utils.brand import COLOR, NAME, footer_text as BRAND_FOOTER

OWNER_ID_ENV = int(os.getenv("OWNER_ID", "0"))

def _footer_text() -> str:
    # brand.footer_text may be a string or a callable; normalize to string
    try:
        return BRAND_FOOTER() if callable(BRAND_FOOTER) else str(BRAND_FOOTER)
    except Exception:
        return "Zephyra • Developed by Polarix1954"

async def is_owner(interaction: discord.Interaction) -> bool:
    if OWNER_ID_ENV and interaction.user.id == OWNER_ID_ENV:
        return True
    try:
        app = await interaction.client.application_info()
        if app.team:
            return interaction.user.id in [m.id for m in app.team.members]
        return interaction.user.id == app.owner.id
    except Exception:
        return False

class Ops(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    ops = app_commands.Group(name="ops", description="Owner/Ops utilities")

    @ops.command(name="ping", description="Latency & health check")
    async def ping(self, interaction: discord.Interaction):
        if not await is_owner(interaction):
            return await interaction.response.send_message("Owner only.", ephemeral=True)
        ws = round(self.bot.latency * 1000)
        e = discord.Embed(title=f"{NAME} Ops", description=f"WebSocket: **{ws} ms**", color=COLOR)
        e.set_footer(text=_footer_text())
        await interaction.response.send_message(embed=e, ephemeral=True)

    @ops.command(name="reload", description="Reload a cog module, e.g. cogs.translate")
    @app_commands.describe(cog="Module path (e.g. cogs.translate)")
    async def reload(self, interaction: discord.Interaction, cog: str):
        if not await is_owner(interaction):
            return await interaction.response.send_message("Owner only.", ephemeral=True)
        t0 = time.perf_counter()
        try:
            await interaction.client.reload_extension(cog)
            ms = int((time.perf_counter() - t0) * 1000)
            e = discord.Embed(description=f"✅ Reloaded `{cog}` in **{ms} ms**", color=COLOR)
        except Exception as exc:
            e = discord.Embed(description=f"❌ Reload failed for `{cog}`:\n`{exc}`", color=COLOR)
        e.set_footer(text=_footer_text())
        await interaction.response.send_message(embed=e, ephemeral=True)

    @ops.command(name="selftest", description="Run a quick self-test")
    async def selftest(self, interaction: discord.Interaction):
        if not await is_owner(interaction):
            return await interaction.response.send_message("Owner only.", ephemeral=True)
        ok = True
        notes = []
        # basic checks
        if not self.bot.user:
            ok = False
            notes.append("No bot.user")
        if self.bot.latency is None:
            ok = False
            notes.append("No latency")
        status = "✅ All good." if ok else "⚠️ Issues: " + ", ".join(notes)
        e = discord.Embed(title="Self-Test", description=status, color=COLOR)
        e.set_footer(text=_footer_text())
        await interaction.response.send_message(embed=e, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Ops(bot))
