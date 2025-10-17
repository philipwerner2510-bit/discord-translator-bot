# cogs/admincommands.py
import re
import discord
from discord.ext import commands
from discord import app_commands
from utils import database

# Regex for custom Discord emoji
CUSTOM_EMOJI_RE = re.compile(r"<(a?):([a-zA-Z0-9_]+):(\d+)>")

# List of supported language codes
SUPPORTED_LANGS = [
    "en", "de", "fr", "es", "it", "pt", "nl", "ru", "ja", "ko", "zh"
]

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -----------------------
    # Set server default language
    # -----------------------
    @app_commands.command(name="defaultlang", description="Set the default translation language for this server.")
    async def defaultlang(self, interaction: discord.Interaction, lang: str):
        guild_id = interaction.guild.id if interaction.guild else None
        if guild_id is None:
            await interaction.response.send_message(
                "❌ Cannot set default language outside a server.", ephemeral=True
            )
            return

        lang = lang.lower()
        if lang not in SUPPORTED_LANGS:
            await interaction.response.send_message(
                f"❌ Invalid language code. Supported codes: {', '.join(SUPPORTED_LANGS)}",
                ephemeral=True
            )
            return

        try:
            await database.set_server_lang(guild_id, lang)
            await interaction.response.send_message(
                f"✅ Server default language set to `{lang}`.", ephemeral=True
            )
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    # -----------------------
    # Multi-select translation channels
    # -----------------------
    @app_commands.command(name="channelselection", description="Select channels where the bot reacts to messages for translation.")
    async def channelselection(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message(
                "❌ This command can only be used in a server.", ephemeral=True
            )
            return

        options = [
            discord.SelectOption(label=ch.name, value=str(ch.id))
            for ch in guild.text_channels
        ]

        select = discord.ui.Select(
            placeholder="Select translation channels...",
            min_values=1,
            max_values=min(len(options), 25),  # Discord max is 25
            options=options
        )

        async def select_callback(select_interaction: discord.Interaction):
            selected_ids = [int(val) for val in select.values]
            await database.set_translation_channels(guild.id, selected_ids)
            mentions = ", ".join(f"<#{id}>" for id in selected_ids)
            await select_interaction.response.send_message(
                f"✅ Translation channels set: {mentions}", ephemeral=True
            )

        select.callback = select_callback
        view = discord.ui.View(timeout=60)  # Auto-disable after 60 seconds
        view.add_item(select)

        await interaction.response.send_message(
            "Select the channels for translation:", view=view, ephemeral=True
        )

    # -----------------------
    # Set error channel
    # -----------------------
    @app_commands.command(name="seterrorchannel", description="Define the error logging channel for your server.")
    async def seterrorchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        guild_id = interaction.guild.id if interaction.guild else None
        if guild_id is None:
            await interaction.response.send_message(
                "❌ Cannot set error channel outside a server.", ephemeral=True
            )
            return

        try:
            await database.set_error_channel(guild_id, channel.id)
            await interaction.response.send_message(
                f"✅ Error channel set to {channel.mention}.", ephemeral=True
            )
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    # -----------------------
    # Set bot emote
    # -----------------------
    @app_commands.command(name="emote", description="Set the bot's reaction emote for translation channels.")
    async def emote(self, interaction: discord.Interaction, emote: str):
        guild_id = interaction.guild.id if interaction.guild else None
        if guild_id is None:
            await interaction.response.send_message(
                "❌ Cannot set emote outside a server.", ephemeral=True
            )
            return

        emote = emote.strip()
        # Validate emote: either 1 unicode character or custom Discord emoji
        if not (len(emote) == 1 or CUSTOM_EMOJI_RE.match(emote)):
            await interaction.response.send_message(
                "❌ Invalid emote. Use a single emoji or a custom server emoji like <:name:id>.", ephemeral=True
            )
            return

        try:
            await database.set_bot_emote(guild_id, emote)
            await interaction.response.send_message(
                f"✅ Bot reaction emote set to {emote}.", ephemeral=True
            )
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
