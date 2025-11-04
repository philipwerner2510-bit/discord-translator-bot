# cogs/owner_commands.py
import discord
from discord.ext import commands
from discord import app_commands

OWNER_ID = 762267166031609858  # Polarix

class OwnerOnly(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ownerping", description="(Owner) Quick sanity ping for owner cog.")
    async def ownerping(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            return await interaction.response.send_message("Nope.", ephemeral=True)
        await interaction.response.send_message("👑 Owner cog loaded and responding.", ephemeral=True)

async def setup(bot: commands.Bot):
    print("[owner_commands] setup() called")
    await bot.add_cog(OwnerOnly(bot))
    print("[owner_commands] cog added")
