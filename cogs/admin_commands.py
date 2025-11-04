# cogs/admin_commands.py  (UPDATED)
import re
import discord
from discord.ext import commands
from discord import app_commands
from utils import database
from utils.config import SUPPORTED_LANGS

CUSTOM_EMOJI_RE = re.compile(r"<(a?):([a-zA-Z0-9_]+):(\d+)>")

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(lang="Two-letter language code (e.g., en, de, fr)")
    @app_commands.command(name="defaultlang", description="Set the default translation language for this server.")
    async def defaultlang(self, interaction: discord.Interaction, lang: str):
        lang = lang.lower()
        if lang not in SUPPORTED_LANGS:
            await interaction.response.send_message(
                f"❌ Invalid language code. Supported: {', '.join(SUPPORTED_LANGS)}", ephemeral=True
            ); return
        await database.set_server_lang(interaction.guild.id, lang)
        await interaction.response.send_message(f"✅ Server default language set to `{lang}`.", ephemeral=True)

    @defaultlang.autocomplete("lang")
    async def defaultlang_autocomplete(self, interaction: discord.Interaction, current: str):
        cur = (current or "").lower()
        return [app_commands.Choice(name=c, value=c) for c in SUPPORTED_LANGS if cur in c][:25]

    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(name="channelselection", description="Select channels where the bot reacts to messages for translation.")
    async def channelselection(self, interaction: discord.Interaction):
        guild = interaction.guild
        channels = sorted(guild.text_channels, key=lambda c: (c.category_id or 0, c.position))
        options = [discord.SelectOption(label=ch.name[:100], value=str(ch.id)) for ch in channels[:25]]
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
        async def on_timeout():
            for item in view.children:
                item.disabled = True
            try:
                await interaction.edit_original_response(view=view)
            except discord.HTTPException:
                pass
        view.on_timeout = on_timeout
        view.add_item(select)
        await interaction.response.send_message("Select the channels for translation:", view=view, ephemeral=True)

    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(channel="Error logging channel (leave empty to clear)")
    @app_commands.command(name="seterrorchannel", description="Define or clear the error logging channel for your server.")
    async def seterrorchannel(self, interaction: discord.Interaction, channel: discord.TextChannel | None):
        gid = interaction.guild.id
        if channel is None:
            await database.set_error_channel(gid, None)
            await interaction.response.send_message("✅ Error channel removed.", ephemeral=True); return
        await database.set_error_channel(gid, channel.id)
        await interaction.response.send_message(f"✅ Error channel set to {channel.mention}.", ephemeral=True)

    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(emote="Emoji or custom emoji mention")
    @app_commands.command(name="emote", description="Set the bot's reaction emote for translation channels.")
    async def emote(self, interaction: discord.Interaction, emote: str):
        guild = interaction.guild
        m = CUSTOM_EMOJI_RE.match(emote.strip())
        if m:
            emoji_id = int(m.group(3))
            if not any(e.id == emoji_id for e in guild.emojis):
                await interaction.response.send_message("❌ I can’t use that custom emoji in this server.", ephemeral=True)
                return
        await database.set_bot_emote(guild.id, emote.strip())
        await interaction.response.send_message(f"✅ Bot reaction emote set to {emote}.", ephemeral=True)

    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(name="settings", description="Show current server settings for the bot.")
    async def settings(self, interaction: discord.Interaction):
        guild = interaction.guild
        gid = guild.id
        default_lang = await database.get_server_lang(gid) or "Not set"
        emote = await database.get_bot_emote(gid) or "🔃"
        error_ch_id = await database.get_error_channel(gid)
        if error_ch_id:
            error_channel = guild.get_channel(error_ch_id)
            error_channel_name = error_channel.mention if error_channel else f"❌ Invalid Channel (ID {error_ch_id})"
        else:
            error_channel_name = "Not set"
        channel_ids = await database.get_translation_channels(gid)
        channel_mentions = ", ".join(f"<#{cid}>" for cid in channel_ids) if channel_ids else "None"
        embed = discord.Embed(title="🛠️ Server Settings", color=0xDE002A)
        embed.add_field(name="Default Language", value=default_lang, inline=False)
        embed.add_field(name="Bot Emote", value=emote, inline=False)
        embed.add_field(name="Error Channel", value=error_channel_name, inline=False)
        embed.add_field(name="Translation Channels", value=channel_mentions, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="langlist", description="Show all supported translation languages with codes.")
    async def langlist(self, interaction: discord.Interaction):
        codes = SUPPORTED_LANGS
        rows = []
        for i in range(0, len(codes), 3):
            rows.append("   |   ".join(f"`{code}`" for code in codes[i:i+3]))
        embed = discord.Embed(title="🌐 Translator Language Codes", description="\n".join(rows), color=0xDE002A)
        embed.set_footer(text=f"Total languages: {len(codes)}")
        await interaction.response.send_message(embed=embed, ephemeral=False)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))