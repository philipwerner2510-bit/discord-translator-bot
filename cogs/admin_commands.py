import re, discord
from discord.ext import commands
from discord import app_commands
from utils import database
from utils.brand import COLOR, footer
from utils.language_data import SUPPORTED_LANGUAGES, label, codes

CUSTOM_EMOJI_RE = re.compile(r"<(a?):([a-zA-Z0-9_]+):(\d+)>")

async def ac_lang(interaction, current: str):
    cur = (current or "").lower()
    out = []
    for l in SUPPORTED_LANGUAGES:
        disp = label(l["code"])
        if cur in l["code"] or cur in l["name"].lower() or cur in disp.lower():
            out.append(app_commands.Choice(name=disp, value=l["code"]))
        if len(out)>=25: break
    return out

class AdminCommands(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.guild_only()
    @app_commands.command(name="defaultlang", description="Set the default translation language for this server.")
    @app_commands.autocomplete(lang=ac_lang)
    async def defaultlang(self, interaction: discord.Interaction, lang: str):
        await interaction.response.defer(ephemeral=True)
        lang = (lang or "").lower().strip()
        if lang not in codes():
            e = discord.Embed(description=f"Unsupported language code `{lang}`.", color=COLOR); e.set_footer(text=footer())
            return await interaction.followup.send(embed=e, ephemeral=True)
        await database.set_server_lang(interaction.guild.id, lang)
        e = discord.Embed(description=f"✅ Server default language set to {label(lang)}.", color=COLOR); e.set_footer(text=footer())
        await interaction.followup.send(embed=e, ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="channelselection", description="Select channels where the bot reacts to messages for translation.")
    async def channelselection(self, interaction: discord.Interaction):
        guild = interaction.guild
        options = [discord.SelectOption(label=ch.name, value=str(ch.id)) for ch in guild.text_channels]
        select = discord.ui.Select(placeholder="Select translation channels…", min_values=1, max_values=min(25, len(options)), options=options)
        async def cb(it: discord.Interaction):
            ids = [int(v) for v in select.values]
            await database.set_translation_channels(guild.id, ids)
            e = discord.Embed(description=f"✅ Translation channels set: {', '.join(f'<#{i}>' for i in ids)}", color=COLOR)
            e.set_footer(text=footer()); await it.response.send_message(embed=e, ephemeral=True)
        select.callback = cb
        view = discord.ui.View(timeout=60); view.add_item(select)
        e = discord.Embed(description="Select the channels for translation:", color=COLOR); e.set_footer(text=footer())
        await interaction.response.send_message(embed=e, view=view, ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="seterrorchannel", description="Set/remove the error logging channel. Pass 'none' to remove.")
    async def seterrorchannel(self, interaction: discord.Interaction, channel: str):
        gid = interaction.guild.id
        if channel.lower()=="none":
            await database.set_error_channel(gid, None)
            e = discord.Embed(description="✅ Error channel removed.", color=COLOR); e.set_footer(text=footer())
            return await interaction.response.send_message(embed=e, ephemeral=True)
        target = None
        try:
            if channel.startswith("<#") and channel.endswith(">"):
                target = interaction.guild.get_channel(int(channel[2:-1]))
            else:
                target = interaction.guild.get_channel(int(channel))
        except Exception:
            target=None
        if not target:
            e = discord.Embed(description="❌ Invalid channel.", color=COLOR); e.set_footer(text=footer())
            return await interaction.response.send_message(embed=e, ephemeral=True)
        await database.set_error_channel(gid, target.id)
        e = discord.Embed(description=f"✅ Error channel set to {target.mention}.", color=COLOR); e.set_footer(text=footer())
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="emote", description="Set the bot's reaction emote for translation channels.")
    async def emote(self, interaction: discord.Interaction, emote: str):
        gid = interaction.guild.id
        if not emote.strip():
            e = discord.Embed(description="❌ Invalid emote.", color=COLOR); e.set_footer(text=footer())
            return await interaction.response.send_message(embed=e, ephemeral=True)
        await database.set_bot_emote(gid, emote.strip())
        e = discord.Embed(description=f"✅ Bot reaction emote set to {emote}.", color=COLOR); e.set_footer(text=footer())
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="settings", description="Show current server settings.")
    async def settings(self, interaction: discord.Interaction):
        gid = interaction.guild.id
        default_lang = await database.get_server_lang(gid) or "Not set"
        emote = await database.get_bot_emote(gid) or "🔃"
        err_ch_id = await database.get_error_channel(gid)
        err_ch_name = "Not set"
        if err_ch_id:
            ch = interaction.guild.get_channel(err_ch_id)
            err_ch_name = ch.mention if ch else f"❌ Invalid Channel (ID {err_ch_id})"
        channels = await database.get_translation_channels(gid)
        channel_mentions = ", ".join(f"<#{cid}>" for cid in channels) if channels else "None"

        e = discord.Embed(title="🛠️ Server Settings", color=COLOR)
        try:
            e.add_field(name="Default Language", value=label(default_lang) if len(default_lang)==2 else default_lang, inline=False)
        except Exception:
            e.add_field(name="Default Language", value=str(default_lang), inline=False)
        e.add_field(name="Bot Emote", value=emote, inline=False)
        e.add_field(name="Error Channel", value=err_ch_name, inline=False)
        e.add_field(name="Translation Channels", value=channel_mentions, inline=False)
        e.set_footer(text=footer())
        await interaction.response.send_message(embed=e, ephemeral=True)

async def setup(bot): await bot.add_cog(AdminCommands(bot))
