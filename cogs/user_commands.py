import discord
from discord import app_commands
from discord.ext import commands
from utils import database as db
from cogs.translate import TranslateCog

class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setmylang", description="Set your personal translation language")
    async def setmylang(self, interaction: discord.Interaction, lang: str):
        await interaction.response.defer(ephemeral=True)
        # Save user language persistently
        await db.set_user_lang(interaction.user.id, lang.lower())
        await interaction.followup.send(f"✅ Your personal language has been set to `{lang}`")

    @app_commands.command(name="translate", description="Translate a message manually")
    async def translate(self, interaction: discord.Interaction, message: str, lang: str):
        await interaction.response.defer(ephemeral=True)
        translator: TranslateCog = self.bot.get_cog("TranslateCog")
        translated = await translator.translate_text(message, lang.lower())
        await interaction.followup.send(f"🌐 Translation ({lang}): {translated}", ephemeral=True)

    @app_commands.command(name="help", description="Show bot commands")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(title="Demon Translator Bot Commands", color=0xDE002A)
        if interaction.user.guild_permissions.administrator:
            embed.add_field(name="/defaultlang", value="Set server default language", inline=False)
            embed.add_field(name="/channelselection", value="Select channels for translation reactions", inline=False)
            embed.add_field(name="/seterrorchannel", value="Set error logging channel", inline=False)
        # Everyone can use
        embed.add_field(name="/setmylang", value="Set your personal translation language", inline=False)
        embed.add_field(name="/translate", value="Translate a message manually", inline=False)
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(UserCommands(bot))
