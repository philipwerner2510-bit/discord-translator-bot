import discord
from discord.ext import commands
from discord import app_commands
from utils import database

class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -----------------------
    # Set My Language (per user)
    # -----------------------
    @app_commands.command(name="setmylang", description="Set your personal translation language.")
    async def setmylang(self, interaction: discord.Interaction, lang: str):
        await interaction.response.defer(ephemeral=True)
        try:
            await database.set_user_lang(interaction.user.id, lang.lower())
            await interaction.followup.send(f"✅ Your personal language has been set to `{lang}`.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error setting your language: {e}", ephemeral=True)

    # -----------------------
    # Help command
