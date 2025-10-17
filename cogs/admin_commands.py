# cogs/admincommands.py
import re
import discord
from discord.ext import commands
from discord import app_commands
from utils import database
import emoji  # pip install emoji

# Regex for custom Discord emoji
CUSTOM_EMOJI_RE = re.compile(r"<(a?):([a-zA-Z0-9_]+):(\d+)>")

# List of supported language codes (used in translator)
SUPPORTED_LANGS = [
    "en", "zh", "hi", "es", "fr", "ar", "bn", "pt", "ru", "ja",
    "de", "jv", "ko", "vi", "mr", "ta", "ur", "tr", "it", "th",
    "gu", "kn", "ml", "pa", "or", "fa", "sw", "am", "ha", "yo"
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

        # Validate: either a custom Discord emoji or a Unicode emoji (includes flags)
        is_custom = CUSTOM_EMOJI_RE.match(emote) is not None
        is_unicode = emoji.is_emoji(emote)

        if not (is_custom or is_unicode):
            await interaction.response.send_message(
                "❌ Invalid emote. Use a valid emoji (including flags) or custom server emoji like <:name:id>.", 
                ephemeral=True
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

    # -----------------------
    # List supported languages (top 30) with flag, code, and name
    # -----------------------
    @app_commands.command(name="langlist", description="Show all supported translation languages with flags, codes, and names.")
    async def langlist(self, interaction: discord.Interaction):
        """
        Shows an embed listing the top 30 languages with flag emojis, language codes, and language names in 3 columns.
        """
        # Mapping: language code -> (flag emoji, language name)
        lang_info = {
            "en": ("🇬🇧", "English"),
            "zh": ("🇨🇳", "Mandarin Chinese"),
            "hi": ("🇮🇳", "Hindi"),
            "es": ("🇪🇸", "Spanish"),
            "fr": ("🇫🇷", "French"),
            "ar": ("🇸🇦", "Arabic"),
            "bn": ("🇧🇩", "Bengali"),
            "pt": ("🇵🇹", "Portuguese"),
            "ru": ("🇷🇺", "Russian"),
            "ja": ("🇯🇵", "Japanese"),
            "de": ("🇩🇪", "German"),
            "jv": ("🇮🇩", "Javanese"),
            "ko": ("🇰🇷", "Korean"),
            "vi": ("🇻🇳", "Vietnamese"),
            "mr": ("🇮🇳", "Marathi"),
            "ta": ("🇮🇳", "Tamil"),
            "ur": ("🇵🇰", "Urdu"),
            "tr": ("🇹🇷", "Turkish"),
            "it": ("🇮🇹", "Italian"),
            "th": ("🇹🇭", "Thai"),
            "gu": ("🇮🇳", "Gujarati"),
            "kn": ("🇮🇳", "Kannada"),
            "ml": ("🇮🇳", "Malayalam"),
            "pa": ("🇮🇳", "Punjabi"),
            "or": ("🇮🇳", "Odia"),
            "fa": ("🇮🇷", "Persian"),
            "sw": ("🇰🇪", "Swahili"),
            "am": ("🇪🇹", "Amharic"),
            "ha": ("🇳🇬", "Hausa"),
            "yo": ("🇳🇬", "Yoruba"),
        }

        codes = list(lang_info.keys())
        rows = []
        for i in range(0, len(codes), 3):
            row_items = []
            for j in range(3):
                if i + j < len(codes):
                    code = codes[i + j]
                    flag, name = lang_info[code]
                    row_items.append(f"{flag} `{code}` {name}")
            rows.append("   |   ".join(row_items))

        table_text = "\n".join(rows)

        embed = discord.Embed(
            title="🌐 Translator Language Codes",
            description=table_text,
            color=0xde002a
        )
        embed.set_footer(text=f"Total languages: {len(lang_info)}")

        # Send to channel (visible to everyone)
        await interaction.response.send_message(embed=embed, ephemeral=False)


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
