import discord
from discord.ext import commands
from discord import app_commands
from utils.brand import COLOR, footer_text

OWNER_ID = 762267166031609858  # <- Your ID


def owner_only(interaction: discord.Interaction):
    return interaction.user.id == OWNER_ID


class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.check(owner_only)
    @app_commands.command(name="owner", description="Owner utilities for Zephyra.")
    async def owner_group(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="👑 Owner Panel",
            description="Private system utilities",
            color=COLOR,
        )
        embed.set_footer(text=footer_text())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @owner_group.command(name="reload", description="Reload bot extensions / cogs.")
    async def reload_cmd(self, interaction: discord.Interaction):
        failures = []
        for ext in list(self.bot.extensions.keys()):
            try:
                await self.bot.reload_extension(ext)
            except Exception:
                failures.append(ext)

        txt = (
            "🔄 Reload complete.\n"
            + (f"❌ Failed: {', '.join(failures)}" if failures else "✅ All cogs reloaded")
        )
        await interaction.response.send_message(txt, ephemeral=True)

    @owner_group.command(name="stats", description="Bot uptime and command count.")
    async def stats_cmd(self, interaction: discord.Interaction):
        cmds = len(self.bot.tree.get_commands())
        embed = discord.Embed(
            title="📊 Zephyra Stats",
            description=f"Registered commands: **{cmds}**",
            color=COLOR,
        )
        embed.set_footer(text=footer_text())
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    cog = Owner(bot)
    await bot.add_cog(cog)

    # ✅ Prevent CommandAlreadyRegistered
    existing = {cmd.name for cmd in bot.tree.get_commands()}
    if "owner" not in existing:
        bot.tree.add_command(cog.owner_group)