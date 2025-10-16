import discord
from discord import app_commands
from discord.ext import commands
from utils import database as db
from cogs.translate import TranslateCog

class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Set personal translation language
    @app_commands.command(name="setmylang", description="Set your personal translation language")
    async def setmylang(self, interaction: discord.Interaction, lang: str):
        await db.set_user_lang(interaction.user.id, lang.lower())
        await interaction.response.send_message(f"✅ Your personal language set to `{lang}`", ephemeral=True)

    # Manual translation command
    @app_commands.command(name="translate", description="Translate a message manually")
    async def translate(self, interaction: discord.Interaction, message: str, lang: str):
        translator: TranslateCog = self.bot.get_cog("TranslateCog")
        translated = await translator.translate_text(message, lang.lower())
        await interaction.response.send_message(f"🌐 Translation ({lang}): {translated}", ephemeral=True)

    # Help command
    @app_commands.command(name="help", description="Shows bot commands")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Demon Translator Bot Commands", color=0xDE002A)
        if interaction.user.guild_permissions.administrator:
            embed.add_field(name="/defaultlang", value="Set default server language", inline=False)
            embed.add_field(name="/channelselection", value="Select channels for reaction translations", inline=False)
            embed.add_field(name="/seterrorchannel", value="Set error logging channel", inline=False)
        # Everyone
        embed.add_field(name="/setmylang", value="Set your personal translation language", inline=False)
        embed.add_field(name="/translate", value="Translate a message manually", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(UserCommands(bot))
