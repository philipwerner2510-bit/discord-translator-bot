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

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # default language (admin)
    @app_commands.guild_only()
    @app_commands.command(name="defaultlang", description="Set the default translation language for this server.")
    @app_commands.describe(lang="Language code (e.g., en, de, fr)")
    @app_commands.autocomplete(lang=lambda it, cur: [
        app_commands.Choice(name=code, value=code)
        for code in SUPPORTED_LANGS if cur.lower() in code][:25]
    )
    async def defaultlang(self, interaction: discord.Interaction, lang: str):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Admins only.", ephemeral=True)
        lang = lang.lower()
        if lang not in SUPPORTED_LANGS:
            return await interaction.response.send_message(f"❌ Invalid language code. Choose from: {', '.join(SUPPORTED_LANGS)}", ephemeral=True)
        await database.set_server_lang(interaction.guild.id, lang)
        await interaction.response.send_message(f"✅ Server default language set to `{lang}`.", ephemeral=True)

    # choose channels (admin)
    @app_commands.guild_only()
    @app_commands.command(name="channelselection", description="Select the text channels where the bot reacts for translation.")
    async def channelselection(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Admins only.", ephemeral=True)
        guild = interaction.guild
        opts = [discord.SelectOption(label=ch.name, value=str(ch.id)) for ch in guild.text_channels[:25]]
        select = discord.ui.Select(placeholder="Select translation channels…", min_values=1, max_values=len(opts), options=opts)
        async def _cb(it: discord.Interaction):
            ids = [int(v) for v in select.values]
            await database.set_translation_channels(guild.id, ids)
            mentions = ", ".join(f"<#{i}>" for i in ids)
            await it.response.send_message(f"✅ Translation channels set: {mentions}", ephemeral=True)
        select.callback = _cb
        v = discord.ui.View(timeout=60)
        v.add_item(select)
        await interaction.response.send_message("Select the channels Zephyra should watch:", view=v, ephemeral=True)

    # set error channel (admin)
    @app_commands.guild_only()
    @app_commands.command(name="seterrorchannel", description="Set or remove the error logging channel. Pass 'none' to clear.")
    async def seterrorchannel(self, interaction: discord.Interaction, channel: str):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Admins only.", ephemeral=True)
        gid = interaction.guild.id
        if channel.lower() == "none":
            await database.set_error_channel(gid, None)
            return await interaction.response.send_message("✅ Error channel removed.", ephemeral=True)

        target = None
        try:
            if channel.startswith("<#") and channel.endswith(">"):
                cid = int(channel[2:-1])
            else:
                cid = int(channel)
            target = interaction.guild.get_channel(cid)
        except Exception:
            pass
        if not target or not isinstance(target, discord.TextChannel):
            return await interaction.response.send_message("❌ Provide a valid text channel mention or ID.", ephemeral=True)

        await database.set_error_channel(gid, target.id)
        await interaction.response.send_message(f"✅ Error channel set to {target.mention}.", ephemeral=True)

    # improved emote setter (admin)
    @app_commands.guild_only()
    @app_commands.command(name="emote", description="Set the reaction emote (Unicode or a custom emoji from this server).")
    @app_commands.describe(emote="Paste a Unicode emoji (👍) or a custom emoji from THIS server (<:name:id>)")
    async def emote(self, interaction: discord.Interaction, emote: str):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Admins only.", ephemeral=True)
        emote = emote.strip()

        ok = False
        preview = None

        # Unicode?
        if not CUSTOM_EMOJI_RE.match(emote):
            # basic unicode - try add on the invoking channel's last message preview by sending and reacting?
            ok = True
            preview = emote
        else:
            # Custom — must belong to this guild
            m = CUSTOM_EMOJI_RE.match(emote)
            _a, name, eid = m.groups()
            eid = int(eid)
            if interaction.guild.get_emoji(eid):
                ok = True
                preview = emote
            else:
                ok = False

        if not ok:
            return await interaction.response.send_message("❌ That custom emoji is not from this server or invalid. Use a Unicode emoji or a custom emoji uploaded here.", ephemeral=True)

        await database.set_bot_emote(interaction.guild.id, emote)
        await interaction.response.send_message(f"✅ Reaction emote set to {preview}", ephemeral=True)

    # settings overview (admin)
    @app_commands.guild_only()
    @app_commands.command(name="settings", description="Show Zephyra’s server settings.")
    async def settings(self, interaction: discord.Interaction):
        gid = interaction.guild.id
        default_lang = await database.get_server_lang(gid) or "—"
        emote = await database.get_bot_emote(gid) or "🔃"
        err_ch_id = await database.get_error_channel(gid)
        err_ch = interaction.guild.get_channel(err_ch_id) if err_ch_id else None
        ch_ids = await database.get_translation_channels(gid) or []
        chs = ", ".join(f"<#{c}>" for c in ch_ids) if ch_ids else "None"

        embed = discord.Embed(title="Server Settings", color=0x00E6F6)
        embed.add_field(name="Default Language", value=default_lang, inline=True)
        embed.add_field(name="Reaction Emote", value=emote, inline=True)
        embed.add_field(name="Error Channel", value=err_ch.mention if err_ch else "Not set", inline=False)
        embed.add_field(name="Translation Channels", value=chs, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))