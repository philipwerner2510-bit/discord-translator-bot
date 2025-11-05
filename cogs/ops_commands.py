# cogs/ops_commands.py
from __future__ import annotations
import typing as T
import discord
from discord import app_commands
from discord.ext import commands

from utils.brand import ACCENT, NAME

class Ops(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Create a namespaced slash group to avoid /settings collision
    ops = app_commands.Group(
        name="ops",
        description="Operational & diagnostic tools",
        guild_only=False,
    )

    @ops.command(name="ping", description="Latency check (gateway & REST).")
    async def ops_ping(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        gw = round(self.bot.latency * 1000)
        msg = await interaction.followup.send("Measuring REST…", ephemeral=True, wait=True)
        rest = (msg.created_at - interaction.created_at).total_seconds() * 1000
        embed = (
            discord.Embed(
                title="Ops • Ping",
                description=f"🛰️ Gateway: **{gw} ms**\n🌐 REST: **{rest:.0f} ms**",
                color=ACCENT,
            )
            .set_author(name=NAME)
        )
        await msg.edit(content=None, embed=embed)

    @ops.command(name="sync", description="Resync slash commands.")
    @app_commands.checks.has_permissions(administrator=True)
    async def ops_sync(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        await self.bot.tree.sync()
        await interaction.followup.send("✅ Slash commands synced.", ephemeral=True)

    @ops.command(name="reload", description="Hot-reload all cogs.")
    @app_commands.checks.has_permissions(administrator=True)
    async def ops_reload(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        failed: list[str] = []
        for ext in list(self.bot.extensions.keys()):
            try:
                await self.bot.reload_extension(ext)
            except Exception:
                failed.append(ext)
        note = "All cogs reloaded." if not failed else f"Reloaded with issues: {', '.join(failed)}"
        await interaction.followup.send(f"♻️ {note}", ephemeral=True)

    @ops.command(name="selftest", description="Run a short health check.")
    async def ops_selftest(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        checks = [
            ("Gateway", True),
            ("Command tree", bool(self.bot.tree.get_commands())),
            ("Intents", self.bot.intents.message_content),
        ]
        lines = [f"{'✅' if ok else '❌'} {label}" for label, ok in checks]
        await interaction.followup.send("**Self-test**\n" + "\n".join(lines), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Ops(bot))
    # Register the group explicitly (important for discord.py 2.x)
    bot.tree.add_command(Ops.ops)
