# cogs/admin_commands.py
import discord
from discord.ext import commands
from discord import app_commands

from utils import database
from utils.language_data import SUPPORTED_LANGUAGES, label

try:
    from utils.brand import COLOR
except Exception:
    COLOR = 0x00E6F6
try:
    from utils.brand import FOOTER as BRAND_FOOTER
except Exception:
    BRAND_FOOTER = "Zephyra • /help for commands"

def _lang_codes():
    return [l["code"] for l in SUPPORTED_LANGUAGES]

async def ac_lang(interaction: discord.Interaction, current: str):
    cur = (current or "").lower()
    choices = []
    for l in SUPPORTED_LANGUAGES:
        disp = label(l["code"])
        if cur in l["code"] or cur in l["name"].lower() or cur in disp.lower():
            choices.append(app_commands.Choice(name=f"{disp} ({l['code']})", value=l["code"]))
        if len(choices) >= 25:
            break
    return choices

class AdminCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---- languages ----
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(name="defaultlang", description="Set the server default language.")
    @app_commands.autocomplete(code=ac_lang)
    async def defaultlang(self, interaction: discord.Interaction, code: str):
        code = (code or "").lower()
        if code not in _lang_codes():
            e = discord.Embed(description=f"❌ Unsupported language code `{code}`.", color=COLOR)
            e.set_footer(text=BRAND_FOOTER)
            return await interaction.response.send_message(embed=e, ephemeral=True)

        await database.set_server_lang(interaction.guild.id, code)
        e = discord.Embed(
            description=f"✅ Server language set to **{label(code)}** (`{code}`).",
            color=COLOR
        )
        e.set_footer(text=BRAND_FOOTER)
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(name="settings", description="Show translation & bot settings.")
    async def settings(self, interaction: discord.Interaction):
        gid = interaction.guild.id
        server_lang = await database.get_server_lang(gid)
        allowed = await database.get_translation_channels(gid)
        emote = await database.get_bot_emote(gid)
        err_ch = await database.get_error_channel(gid)

        chans = "All channels (no allow-list)" if not allowed else ", ".join(f"<#{cid}>" for cid in allowed)
        lang_disp = label(server_lang) if server_lang else "Not set"

        e = discord.Embed(title="⚙️ Server Settings", color=COLOR)
        e.add_field(name="Server Language", value=f"{lang_disp} `{server_lang or ''}`", inline=False)
        e.add_field(name="Translate Emote", value=emote or "🔃", inline=True)
        e.add_field(name="Error Channel", value=f"<#{err_ch}>" if err_ch else "None", inline=True)
        e.add_field(name="Allowed Channels", value=chans, inline=False)
        e.set_footer(text=BRAND_FOOTER)
        await interaction.response.send_message(embed=e, ephemeral=True)

    # ---- meta shortcuts kept (you said they worked; unchanged behavior) ----
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(name="setemote", description="Set the translation reaction emote.")
    async def setemote(self, interaction: discord.Interaction, emote: str):
        await database.set_bot_emote(interaction.guild.id, emote.strip())
        e = discord.Embed(description=f"✅ Emote set to {emote}", color=COLOR)
        e.set_footer(text=BRAND_FOOTER)
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(name="seterrorchannel", description="Set or clear the error channel.")
    async def seterrorchannel(self, interaction: discord.Interaction, channel: discord.TextChannel | None):
        await database.set_error_channel(interaction.guild.id, channel.id if channel else None)
        e = discord.Embed(description=f"✅ Error channel set to {channel.mention if channel else 'None'}", color=COLOR)
        e.set_footer(text=BRAND_FOOTER)
        await interaction.response.send_message(embed=e, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCommands(bot))
