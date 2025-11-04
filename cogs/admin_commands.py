# cogs/admin_commands.py
import re
import discord
from discord.ext import commands
from discord import app_commands
from utils import database

BOT_COLOR = 0xDE002A
CUSTOM_EMOJI_RE = re.compile(r"<(a?):([a-zA-Z0-9_]+):(\d+)>")

LANG_CATALOG = [
    ("en","🇬🇧","English"), ("de","🇩🇪","German"), ("fr","🇫🇷","French"), ("es","🇪🇸","Spanish"),
    ("it","🇮🇹","Italian"), ("pt","🇵🇹","Portuguese"), ("ru","🇷🇺","Russian"), ("zh","🇨🇳","Chinese"),
    ("ja","🇯🇵","Japanese"), ("ko","🇰🇷","Korean"), ("ar","🇸🇦","Arabic"), ("tr","🇹🇷","Turkish"),
    ("nl","🇳🇱","Dutch"), ("sv","🇸🇪","Swedish"), ("no","🇳🇴","Norwegian"), ("da","🇩🇰","Danish"),
    ("fi","🇫🇮","Finnish"), ("pl","🇵🇱","Polish"), ("cs","🇨🇿","Czech"), ("el","🇬🇷","Greek"),
    ("uk","🇺🇦","Ukrainian"), ("he","🇮🇱","Hebrew"), ("vi","🇻🇳","Vietnamese"), ("th","🇹🇭","Thai"),
    ("id","🇮🇩","Indonesian"), ("ms","🇲🇾","Malay"), ("fa","🇮🇷","Persian"), ("sw","🇰🇪","Swahili"),
]
SUPPORTED = {c for c,_,_ in LANG_CATALOG}

def _choices(q: str):
    q = (q or "").lower().strip()
    vals=[]
    for code, flag, name in LANG_CATALOG:
        if not q or q in code or q in name.lower():
            vals.append(app_commands.Choice(name=f"{flag} {name} ({code})"[:100], value=code))
        if len(vals) >= 25: break
    return vals or [app_commands.Choice(name=f"{f} {n} ({c})"[:100], value=c)
                    for c,f,n in LANG_CATALOG[:25]]

async def lang_autocomplete(_itx: discord.Interaction, current: str):
    return _choices(current)

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.guild_only()
    @app_commands.autocomplete(lang=lang_autocomplete)
    @app_commands.command(name="defaultlang", description="Set the default translation language for this server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def defaultlang(self, interaction: discord.Interaction, lang: str):
        lang = lang.lower()
        if lang not in SUPPORTED:
            return await interaction.response.send_message("❌ Invalid language code.", ephemeral=True)
        await database.set_server_lang(interaction.guild.id, lang)
        await interaction.response.send_message(f"✅ Server default language set to `{lang}`.", ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="channelselection", description="Select channels where the bot reacts to translate.")
    @app_commands.checks.has_permissions(administrator=True)
    async def channelselection(self, interaction: discord.Interaction):
        guild = interaction.guild
        options = [discord.SelectOption(label=ch.name, value=str(ch.id)) for ch in guild.text_channels[:25]]
        select = discord.ui.Select(placeholder="Select translation channels...", min_values=1, max_values=len(options), options=options)

        async def select_callback(itx: discord.Interaction):
            selected = [int(v) for v in select.values]
            await database.set_translation_channels(guild.id, selected)
            await itx.response.send_message(f"✅ Translation channels set: {', '.join(f'<#{i}>' for i in selected)}", ephemeral=True)

        select.callback = select_callback
        v = discord.ui.View(timeout=60)
        v.add_item(select)
        await interaction.response.send_message("Select the channels for translation:", view=v, ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="seterrorchannel", description="Set the error logging channel (or 'none' to remove).")
    @app_commands.checks.has_permissions(administrator=True)
    async def seterrorchannel(self, interaction: discord.Interaction, channel: str):
        gid = interaction.guild.id
        if channel.lower() == "none":
            await database.set_error_channel(gid, None)
            return await interaction.response.send_message("✅ Error channel removed.", ephemeral=True)
        try:
            cid = int(channel[2:-1]) if channel.startswith("<#") and channel.endswith(">") else int(channel)
            ch = interaction.guild.get_channel(cid)
            if not ch: raise ValueError("Invalid channel")
            await database.set_error_channel(gid, ch.id)
            await interaction.response.send_message(f"✅ Error channel set to {ch.mention}.", ephemeral=True)
        except Exception:
            await interaction.response.send_message("❌ Invalid channel. Pass a text channel or 'none'.", ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="emote", description="Set the bot's reaction emoji.")
    @app_commands.checks.has_permissions(administrator=True)
    async def emote(self, interaction: discord.Interaction, emote: str):
        await database.set_bot_emote(interaction.guild.id, emote.strip())
        await interaction.response.send_message(f"✅ Reaction emoji set to {emote}. If invalid, bot auto-falls back to 🔁.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))