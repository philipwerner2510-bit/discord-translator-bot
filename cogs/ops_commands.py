import discord
from discord.ext import commands
from discord import app_commands
from utils.brand import COLOR, footer_text


class Ops(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="ops", description="Zephyra operational utilities.")
    async def ops_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚙️ Operational Tools",
            description="Admin-only bot utilities.",
            color=COLOR,
        )
        embed.set_footer(text=footer_text())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @ops_cmd.command(name="sync", description="Sync slash commands now.")
    async def sync_cmd(self, interaction: discord.Interaction):
        await self.bot.tree.sync()
        await interaction.response.send_message("✅ Synchronized commands.", ephemeral=True)


async def setup(bot: commands.Bot):
    cog = Ops(bot)
    await bot.add_cog(cog)

    # ✅ Prevent CommandAlreadyRegistered
    existing = {cmd.name for cmd in bot.tree.get_commands()}
    if "ops" not in existing:
        bot.tree.add_command(cog.ops_cmd)