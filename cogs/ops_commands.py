import discord
from discord.ext import commands
from discord import app_commands
from utils.brand import COLOR, footer

class Ops(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="settings", description="Quick test & info panel (admins).")
    @app_commands.checks.has_permissions(administrator=True)
    async def settings(self, interaction: discord.Interaction):
        e = discord.Embed(title="Settings Panel", description="Use admin commands to configure the bot.", color=COLOR)
        e.set_footer(text=footer()); await interaction.response.send_message(embed=e, ephemeral=True)

async def setup(bot): await bot.add_cog(Ops(bot))
