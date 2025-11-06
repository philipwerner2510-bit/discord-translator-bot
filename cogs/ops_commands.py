# cogs/ops_commands.py
import time
import importlib
import discord
from discord.ext import commands
from discord import app_commands

from utils.brand import COLOR, NAME
from utils import database

FOOTER = f"{NAME} — Developed by Polarix1954"

OPS_COGS = [
    "cogs.user_commands",
    "cogs.admin_commands",
    "cogs.translate",
    "cogs.events",
    "cogs.ops_commands",
    "cogs.analytics_commands",
    "cogs.invite_command",
    "cogs.welcome",
    "cogs.owner_commands",
    "cogs.context_menu",
    "cogs.xp_system",
]

class Ops(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # create a command group so names don't collide with legacy globals
    ops = app_commands.Group(name="ops", description="Operations utilities", guild_only=True)

    @ops.command(name="ping", description="Show latency.")
    async def ops_ping(self, interaction: discord.Interaction):
        t0 = time.perf_counter()
        await interaction.response.defer(ephemeral=True, thinking=True)
        rt = (time.perf_counter() - t0) * 1000
        e = (discord.Embed(color=COLOR, title="Pong!")
             .add_field(name="Gateway", value=f"{round(self.bot.latency*1000)} ms")
             .add_field(name="Roundtrip", value=f"{rt:.1f} ms")
             .set_footer(text=FOOTER))
        await interaction.followup.send(embed=e, ephemeral=True)

    @ops.command(name="reload", description="Reload a cog or all cogs.")
    @app_commands.describe(cog="Module path (e.g., cogs.translate) or 'all'")
    async def ops_reload(self, interaction: discord.Interaction, cog: str):
        await interaction.response.defer(ephemeral=True, thinking=True)
        count = 0
        errors = []

        targets = OPS_COGS if cog.lower() == "all" else [cog]
        for ext in targets:
            try:
                importlib.invalidate_caches()
                try:
                    await self.bot.unload_extension(ext)
                except Exception:
                    pass
                await self.bot.load_extension(ext)
                count += 1
            except Exception as e:
                errors.append(f"`{ext}` → `{e}`")

        e = discord.Embed(color=COLOR, title="Reload")
        e.description = f"Reloaded **{count}** modules."
        if errors:
            e.add_field(name="Errors", value="\n".join(errors), inline=False)
        e.set_footer(text=FOOTER)
        await interaction.followup.send(embed=e, ephemeral=True)

    @ops.command(name="selftest", description="Run a quick self test.")
    async def ops_selftest(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await database.ensure_schema()
            msg = "DB schema OK."
        except Exception as e:
            msg = f"DB error: {e}"

        e = discord.Embed(color=COLOR, title="Self Test")
        e.description = f"**{msg}**"
        e.set_footer(text=FOOTER)
        await interaction.followup.send(embed=e, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Ops(bot))
