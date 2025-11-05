# cogs/user_commands.py
import os, discord
from discord.ext import commands
from discord import app_commands
from utils import database
from utils.brand import COLOR, EMOJI_PRIMARY, footer
from utils.langs import SUPPORTED_LANGS, LANG_INFO, lang_label

OWNER_ID = int(os.getenv("OWNER_ID", "762267166031609858"))

async def ac_lang(_: discord.Interaction, current: str):
    current = (current or "").lower()
    matches = [c for c in SUPPORTED_LANGS if current in c or current in lang_label(c).lower()]
    return [app_commands.Choice(name=lang_label(c), value=c) for c in matches[:25]]

class UserCommands(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="setmylang", description="Set your personal translation language.")
    @app_commands.describe(lang="Language (code)")
    @app_commands.autocomplete(lang=ac_lang)
    async def setmylang(self, interaction: discord.Interaction, lang: str):
        await interaction.response.defer(ephemeral=True)
        lang = (lang or "").lower().strip()
        if lang not in SUPPORTED_LANGS:
            e = discord.Embed(description=f"❌ Unsupported language code `{lang}`.", color=COLOR)
            e.set_footer(text=footer()); return await interaction.followup.send(embed=e, ephemeral=True)
        await database.set_user_lang(interaction.user.id, lang)
        flag, name = LANG_INFO.get(lang, ("🏳️", "Unknown"))
        e = discord.Embed(description=f"✅ Your personal language is now {flag} `{lang}` — **{name}**.", color=COLOR)
        e.set_footer(text=footer()); await interaction.followup.send(embed=e, ephemeral=True)

    @app_commands.command(name="langlist", description="Show all supported languages.")
    async def langlist(self, interaction: discord.Interaction):
        codes, rows = SUPPORTED_LANGS, []
        for i in range(0, len(codes), 3):
            chunk = codes[i:i+3]; parts=[]
            for c in chunk:
                flag, name = LANG_INFO.get(c, ("🏳️", "Unknown"))
                parts.append(f"{flag} `{c}` {name}")
            rows.append("   |   ".join(parts))
        e = discord.Embed(title=f"{EMOJI_PRIMARY} Supported Languages", description="\n".join(rows), color=COLOR)
        e.set_footer(text=footer()); await interaction.response.send_message(embed=e)

    @app_commands.command(name="help", description="Show Zephyra help.")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        e = discord.Embed(
            title=f"{EMOJI_PRIMARY} Zephyra — Help",
            color=COLOR,
            description=(
                "**Everyone**: `/translate`, `/setmylang`, `/langlist`, `/invite`, `/ping`\n"
                "**Admins**: `/defaultlang`, `/channelselection`, `/emote`, `/seterrorchannel`, `/settings`, `/guide`\n"
                "**Owner**: `/stats`, `/reload`"
            ),
        )
        e.set_footer(text=footer())
        await interaction.followup.send(embed=e, ephemeral=True)

async def setup(bot): await bot.add_cog(UserCommands(bot))