import re
import discord
from discord.ext import commands
from discord import app_commands
from utils import database, logging_utils

CUSTOM_EMOJI_RE = re.compile(r"<(a?):([a-zA-Z0-9_]+):(\d+)>")
SUPPORTED_LANGS = [
    "en", "zh", "hi", "es", "fr", "ar", "bn", "pt", "ru", "ja",
    "de", "jv", "ko", "vi", "mr", "ta", "ur", "tr", "it", "th",
    "gu", "kn", "ml", "pa", "or", "fa", "sw", "am", "ha", "yo"
]

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -----------------------
    # /defaultlang
    # -----------------------
    @app_commands.guild_only()
    @app_commands.command(name="defaultlang", description="Set the default translation language for this server.")
    async def defaultlang(self, interaction: discord.Interaction, lang: str):
        lang = lang.lower()
        if lang not in SUPPORTED_LANGS:
            await interaction.response.send_message(
                f"❌ Invalid language code. Supported: {', '.join(SUPPORTED_LANGS)}", ephemeral=True
            )
            return
        try:
            await database.set_server_lang(interaction.guild.id, lang)
            await interaction.response.send_message(f"✅ Server default language set to `{lang}`.", ephemeral=True)
        except Exception as e:
            await logging_utils.log_error(self.bot, interaction.guild.id, "Failed to set server language", e)
            await interaction.response.send_message("❌ Failed to set server language.", ephemeral=True)

    # -----------------------
    # /setratelimit (NEW)
    # -----------------------
    @app_commands.guild_only()
    @app_commands.command(name="setratelimit", description="Set translations per minute for this server.")
    async def setratelimit(self, interaction: discord.Interaction, limit: int):
        if limit < 1 or limit > 60:
            await interaction.response.send_message("❌ Limit must be between 1 and 60 per minute.", ephemeral=True)
            return
        try:
            await database.set_server_rate_limit(interaction.guild.id, limit)
            await interaction.response.send_message(f"✅ Server translation rate limit set to `{limit}` per minute.", ephemeral=True)
        except Exception as e:
            await logging_utils.log_error(self.bot, interaction.guild.id, "Failed to set server rate limit", e)
            await interaction.response.send_message("❌ Failed to set server rate limit.", ephemeral=True)

    # -----------------------
    # Other existing commands remain unchanged
    # /channelselection, /seterrorchannel, /emote, /langlist
    # -----------------------

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
