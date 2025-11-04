# cogs/admin_commands.py
import re
import discord
from discord.ext import commands
from discord import app_commands
from utils import database
from utils.config import SUPPORTED_LANGS, LANG_META, lang_label

CUSTOM_EMOJI_RE = re.compile(r"<(a?):([a-zA-Z0-9_]+):(\d+)>")


class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -----------------------
    # /defaultlang
    # -----------------------
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(name="defaultlang", description="Set the server default translation language.")
    async def defaultlang(self, interaction: discord.Interaction, lang: str):
        lang = lang.lower()
        if lang not in SUPPORTED_LANGS:
            return await interaction.response.send_message(
                f"❌ Invalid language. Supported: {', '.join(SUPPORTED_LANGS)}", ephemeral=True
            )
        await database.set_server_lang(interaction.guild.id, lang)
        await interaction.response.send_message(f"✅ Server default language set to `{lang}`.", ephemeral=True)

    @defaultlang.autocomplete("lang")
    async def _auto_lang(self, interaction: discord.Interaction, current: str):
        current = (current or "").lower()
        return [
            app_commands.Choice(name=c, value=c)
            for c in SUPPORTED_LANGS if current in c
        ][:25]

    # -----------------------
    # /channelselection
    # -----------------------
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(name="channelselection", description="Select channels for auto-translate reaction.")
    async def channelselection(self, interaction: discord.Interaction):
        options = [
            discord.SelectOption(label=ch.name, value=str(ch.id))
            for ch in interaction.guild.text_channels[:25]
        ]
        select = discord.ui.Select(
            placeholder="Select channels...",
            min_values=1, max_values=len(options), options=options
        )

        async def cb(i: discord.Interaction):
            ids = [int(v) for v in select.values]
            await database.set_translation_channels(interaction.guild.id, ids)
            m = ", ".join(f"<#{c}>" for c in ids)
            await i.response.send_message(f"✅ Channels set: {m}", ephemeral=True)

        select.callback = cb
        view = discord.ui.View()
        view.add_item(select)
        await interaction.response.send_message("Choose channels:", view=view, ephemeral=True)

    # -----------------------
    # /seterrorchannel
    # -----------------------
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(name="seterrorchannel", description="Set or remove error logging channel.")
    async def seterrorchannel(self, interaction: discord.Interaction, channel: str):
        gid = interaction.guild.id
        if channel.lower() == "none":
            await database.set_error_channel(gid, None)
            return await interaction.response.send_message("✅ Error channel removed.", ephemeral=True)

        try:
            if channel.startswith("<#") and channel.endswith(">"):
                channel_id = int(channel[2:-1])
            else:
                channel_id = int(channel)
            ch = interaction.guild.get_channel(channel_id)
        except Exception:
            ch = None

        if not ch:
            return await interaction.response.send_message("❌ Invalid channel.", ephemeral=True)

        await database.set_error_channel(gid, ch.id)
        await interaction.response.send_message(f"✅ Error channel set to {ch.mention}", ephemeral=True)

    # -----------------------
    # /emote
    # -----------------------
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(name="emote", description="Set emoji the bot listens for (unicode or custom).")
    async def emote(self, interaction: discord.Interaction, emote: str):
        await database.set_bot_emote(interaction.guild.id, emote)
        await interaction.response.send_message(f"✅ Set bot reaction emote to {emote}", ephemeral=True)

    # -----------------------
    # /settings
    # -----------------------
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(name="settings", description="Show current bot settings for server.")
    async def settings(self, interaction: discord.Interaction):
        gid = interaction.guild.id
        lang = await database.get_server_lang(gid) or "None"
        emote = await database.get_bot_emote(gid) or "🔃"
        err = await database.get_error_channel(gid)
        chans = await database.get_translation_channels(gid)

        embed = discord.Embed(title="🛠️ Server Settings", color=0xDE002A)
        embed.add_field(name="Default Language", value=lang, inline=False)
        embed.add_field(name="Bot Emote", value=emote, inline=False)
        embed.add_field(name="Error Channel", value=(f"<#{err}>" if err else "None"), inline=False)
        embed.add_field(name="Translation Channels", value=", ".join(f"<#{c}>" for c in chans) or "None", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # -----------------------
    # /langlist  (pretty grid with flags + names)
    # -----------------------
    @app_commands.command(name="langlist", description="Show supported languages (flags + names + codes).")
    async def langlist(self, interaction: discord.Interaction):
        # Sort alphabetically by language name for readability
        codes_sorted = sorted(
            SUPPORTED_LANGS,
            key=lambda c: LANG_META.get(c, ("🌐", c.upper()))[1]
        )

        # Build 3-column grid
        rows = []
        for i in range(0, len(codes_sorted), 3):
            chunk = codes_sorted[i:i+3]
            cells = [lang_label(code) for code in chunk]
            rows.append("   |   ".join(cells))

        desc = "\n".join(rows)
        embed = discord.Embed(
            title="🌍 Supported Languages",
            description=desc if desc else "No languages configured.",
            color=0xDE002A
        )
        embed.set_footer(text=f"Total: {len(SUPPORTED_LANGS)}")

        await interaction.response.send_message(embed=embed, ephemeral=False)


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))