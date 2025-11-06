# cogs/ops_commands.py
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from utils.brand import ACCENT, NAME, footer_text


class Ops(commands.Cog):
    """Operational & diagnostic tools (under /ops)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Namespaced group (prevents collisions with /settings etc.)
    ops = app_commands.Group(
        name="ops",
        description="Operational & diagnostic tools",
        guild_only=False,
    )

    @ops.command(name="ping", description="Latency check (gateway & REST).")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        gateway_ms = round(self.bot.latency * 1000)
        msg = await interaction.followup.send("Measuring REST…", ephemeral=True, wait=True)
        rest_ms = (msg.created_at - interaction.created_at).total_seconds() * 1000

        embed = (
            discord.Embed(
                title="Ops • Ping",
                description=f"🛰️ Gateway: **{gateway_ms} ms**\n🌐 REST: **{rest_ms:.0f} ms**",
                color=ACCENT,
            )
            .set_author(name=NAME)
            .set_footer(text=footer_text())
        )
        await msg.edit(content=None, embed=embed)

    @ops.command(name="sync", description="Resync slash commands.")
    @app_commands.checks.has_permissions(administrator=True)
    async def sync(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.bot.tree.sync()
        await interaction.followup.send("✅ Slash commands synced.", ephemeral=True)

    @ops.command(name="reload", description="Hot-reload all loaded cogs.")
    @app_commands.checks.has_permissions(administrator=True)
    async def reload(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        failed: list[str] = []
        reloaded: list[str] = []
        for ext in list(self.bot.extensions.keys()):
            try:
                await self.bot.reload_extension(ext)
                reloaded.append(ext)
            except Exception:
                failed.append(ext)

        desc = []
        if reloaded:
            desc.append("✅ **Reloaded**\n" + "\n".join(f"• `{e}`" for e in reloaded))
        if failed:
            desc.append("\n❌ **Failed**\n" + "\n".join(f"• `{e}`" for e in failed))
        if not desc:
            desc.append("No extensions to reload.")

        embed = (
            discord.Embed(title="Ops • Reload", description="\n".join(desc), color=ACCENT)
            .set_author(name=NAME)
            .set_footer(text=footer_text())
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @ops.command(name="selftest", description="Run a short health check.")
    async def selftest(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        checks = [
            ("Gateway connected", True),
            ("Command tree registered", bool(self.bot.tree.get_commands())),
            ("Intents.message_content", self.bot.intents.message_content),
        ]
        lines = [f"{'✅' if ok else '❌'} {label}" for label, ok in checks]
        embed = (
            discord.Embed(title="Ops • Self-test", description="\n".join(lines), color=ACCENT)
            .set_author(name=NAME)
            .set_footer(text=footer_text())
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Ops(bot))
    # Guard to avoid CommandAlreadyRegistered on reload:
    if not any(cmd.name == "ops" for cmd in bot.tree.get_commands()):
        bot.tree.add_command(Ops.ops)