import re
import discord
from discord.ext import commands
from discord import app_commands
from utils import database

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
    # Set default server language
    # -----------------------
    @app_commands.guild_only()
    @app_commands.command(name="defaultlang", description="Set the default translation language for this server.")
    async def defaultlang(self, interaction: discord.Interaction, lang: str):
        guild_id = interaction.guild.id
        lang = lang.lower()
        if lang not in SUPPORTED_LANGS:
            await interaction.response.send_message(
                f"❌ Invalid language code. Supported: {', '.join(SUPPORTED_LANGS)}", ephemeral=True
            )
            return
        await database.set_server_lang(guild_id, lang)
        await interaction.response.send_message(f"✅ Server default language set to `{lang}`.", ephemeral=True)

    # -----------------------
    # Select translation channels
    # -----------------------
    @app_commands.guild_only()
    @app_commands.command(name="channelselection", description="Select channels where the bot reacts to messages for translation.")
    async def channelselection(self, interaction: discord.Interaction):
        guild = interaction.guild
        options = [discord.SelectOption(label=ch.name, value=str(ch.id)) for ch in guild.text_channels]
        select = discord.ui.Select(
            placeholder="Select translation channels...",
            min_values=1,
            max_values=min(len(options), 25),
            options=options
        )
        async def select_callback(select_interaction: discord.Interaction):
            selected_ids = [int(val) for val in select.values]
            await database.set_translation_channels(guild.id, selected_ids)
            mentions = ", ".join(f"<#{id}>" for id in selected_ids)
            await select_interaction.response.send_message(f"✅ Translation channels set: {mentions}", ephemeral=True)
        select.callback = select_callback
        view = discord.ui.View(timeout=60)
        view.add_item(select)
        await interaction.response.send_message("Select the channels for translation:", view=view, ephemeral=True)

    # -----------------------
    # Set or remove error channel
    # -----------------------
    @app_commands.guild_only()
    @app_commands.command(name="seterrorchannel", description="Define the error logging channel for your server. Pass 'none' to remove.")
    async def seterrorchannel(self, interaction: discord.Interaction, channel: str):
        guild_id = interaction.guild.id
        if channel.lower() == "none":
            await database.set_error_channel(guild_id, None)
            await interaction.response.send_message(f"✅ Error channel removed.", ephemeral=True)
            return
        # Try to resolve channel by mention or ID
        target_channel = None
        if interaction.guild:
            try:
                # Try mention ID
                if channel.startswith("<#") and channel.endswith(">"):
                    channel_id = int(channel[2:-1])
                    target_channel = interaction.guild.get_channel(channel_id)
                else:
                    channel_id = int(channel)
                    target_channel = interaction.guild.get_channel(channel_id)
            except Exception:
                target_channel = None
        if not target_channel:
            await interaction.response.send_message(f"❌ Invalid channel. Pass a valid text channel or 'none' to remove.", ephemeral=True)
            return
        await database.set_error_channel(guild_id, target_channel.id)
        await interaction.response.send_message(f"✅ Error channel set to {target_channel.mention}.", ephemeral=True)

    # -----------------------
    # Set bot reaction emote
    # -----------------------
    @app_commands.guild_only()
    @app_commands.command(name="emote", description="Set the bot's reaction emote for translation channels.")
    async def emote(self, interaction: discord.Interaction, emote: str):
        guild_id = interaction.guild.id
        emote = emote.strip()
        is_custom = CUSTOM_EMOJI_RE.match(emote) is not None
        is_unicode = len(emote) > 0
        if not (is_custom or is_unicode):
            await interaction.response.send_message("❌ Invalid emote.", ephemeral=True)
            return
        await database.set_bot_emote(guild_id, emote)
        await interaction.response.send_message(f"✅ Bot reaction emote set to {emote}.", ephemeral=True)

    # -----------------------
    # Show server settings
    # -----------------------
    @app_commands.guild_only()
    @app_commands.command(name="settings", description="Show current server settings for the bot.")
    async def settings(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        default_lang = await database.get_server_lang(guild_id) or "Not set"
        emote = await database.get_bot_emote(guild_id) or "🔃"
        error_ch_id = await database.get_error_channel(guild_id)
        if error_ch_id:
            error_channel = interaction.guild.get_channel(error_ch_id)
            error_channel_name = error_channel.mention if error_channel else f"❌ Invalid Channel (ID {error_ch_id})"
        else:
            error_channel_name = "Not set"
        channel_ids = await database.get_translation_channels(guild_id)
        if channel_ids:
            channel_mentions = ", ".join(f"<#{cid}>" for cid in channel_ids)
        else:
            channel_mentions = "None"
        embed = discord.Embed(
            title="🛠️ Server Settings",
            color=0xde002a
        )
        embed.add_field(name="Default Language", value=default_lang, inline=False)
        embed.add_field(name="Bot Emote", value=emote, inline=False)
        embed.add_field(name="Error Channel", value=error_channel_name, inline=False)
        embed.add_field(name="Translation Channels", value=channel_mentions, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # -----------------------
    # Language list (global)
    # -----------------------
    @app_commands.command(name="langlist", description="Show all supported translation languages with flags, codes, and names.")
    async def langlist(self, interaction: discord.Interaction):
        lang_info = {
            "en": ("🇬🇧", "English"), "zh": ("🇨🇳", "Mandarin Chinese"), "hi": ("🇮🇳", "Hindi"),
            "es": ("🇪🇸", "Spanish"), "fr": ("🇫🇷", "French"), "ar": ("🇸🇦", "Arabic"),
            "bn": ("🇧🇩", "Bengali"), "pt": ("🇵🇹", "Portuguese"), "ru": ("🇷🇺", "Russian"),
            "ja": ("🇯🇵", "Japanese"), "de": ("🇩🇪", "German"), "jv": ("🇮🇩", "Javanese"),
            "ko": ("🇰🇷", "Korean"), "vi": ("🇻🇳", "Vietnamese"), "mr": ("🇮🇳", "Marathi"),
            "ta": ("🇮🇳", "Tamil"), "ur": ("🇵🇰", "Urdu"), "tr": ("🇹🇷", "Turkish"), "it": ("🇮🇹", "Italian"),
            "th": ("🇹🇭", "Thai"), "gu": ("🇮🇳", "Gujarati"), "kn": ("🇮🇳", "Kannada"), "ml": ("🇮🇳", "Malayalam"),
            "pa": ("🇮🇳", "Punjabi"), "or": ("🇮🇳", "Odia"), "fa": ("🇮🇷", "Persian"), "sw": ("🇰🇪", "Swahili"),
            "am": ("🇪🇹", "Amharic"), "ha": ("🇳🇬", "Hausa"), "yo": ("🇳🇬", "Yoruba")
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
        embed = discord.Embed(title="🌐 Translator Language Codes", description="\n".join(rows), color=0xde002a)
        embed.set_footer(text=f"Total languages: {len(lang_info)}")
        await interaction.response.send_message(embed=embed, ephemeral=False)


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
