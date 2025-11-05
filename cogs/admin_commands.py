# cogs/admin_commands.py
import re
import discord
from discord.ext import commands
from discord import app_commands
from utils import database

SUPPORTED_LANGS = [
    "en","zh","hi","es","fr","ar","bn","pt","ru","ja",
    "de","jv","ko","vi","mr","ta","ur","tr","it","th",
    "gu","kn","ml","pa","or","fa","sw","am","ha","yo"
]

CUSTOM_EMOJI_RE = re.compile(r"<(a?):([a-zA-Z0-9_]+):(\d+)>")

# --- FIX: autocomplete helper must be async
async def ac_lang(interaction: discord.Interaction, current: str):
    current = (current or "").lower()
    items = [code for code in SUPPORTED_LANGS if current in code]
    return [app_commands.Choice(name=code, value=code) for code in items[:25]]

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.guild_only()
    @app_commands.command(name="defaultlang", description="Set the default translation language for this server.")
    @app_commands.describe(lang="Language code (e.g., en, de, fr)")
    @app_commands.autocomplete(lang=ac_lang)  # <-- FIXED
    async def defaultlang(self, interaction: discord.Interaction, lang: str):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Admins only.", ephemeral=True)
        lang = lang.lower()
        if lang not in SUPPORTED_LANGS:
            return await interaction.response.send_message(
                f"❌ Invalid language code. Choose from: {', '.join(SUPPORTED_LANGS)}",
                ephemeral=True
            )
        await database.set_server_lang(interaction.guild.id, lang)
        await interaction.response.send_message(f"✅ Server default language set to `{lang}`.", ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="channelselection", description="Select the text channels where the bot reacts for translation.")
    async def channelselection(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Admins only.", ephemeral=True)
        guild = interaction.guild
        opts = [discord.SelectOption(label=ch.name, value=str(ch.id)) for ch in guild.text_channels[:25]]
        select = discord.ui.Select(placeholder="Select translation channels…