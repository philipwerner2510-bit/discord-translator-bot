# cogs/user_commands.py
import os, discord
from discord.ext import commands
from discord import app_commands
from utils.brand import COLOR, footer, HELP_TITLE, Z_EXCITED, Z_CONFUSED, Z_HAPPY, Z_LOVE
from utils.language_data import SUPPORTED_LANGUAGES, label, codes
from utils import database

OWNER_ID = int(os.getenv("OWNER_ID", "762267166031609858"))

async def ac_lang(interaction: discord.Interaction, current: str):
    cur = (current or "").lower()
    out = []
    for l in SUPPORTED_LANGUAGES:
        disp = label(l["code"])
        if cur in l["code"] or cur in l["name"].lower() or cur in disp.lower():
            out.append(app_commands.Choice(name=disp, value=l["code"]))
        if len(out) >= 25:
            break
    return out

class HelpTabs(discord.ui.View):
    def __init__(self, is_admin: bool, is_owner: bool):
        super().__init__(timeout=180)
        self.is_admin = is_admin
        self.is_owner = is_owner

    @discord.ui.button(label="General", emoji=Z_EXCITED, style=discord.ButtonStyle.primary)
    async def tab_general(self, it: discord.Interaction, btn: discord.ui.Button):
        e = discord.Embed(
            title="General Commands",
            color=COLOR,
            description=(
                "• `/help` — open this menu\n"
                "• `/invite` — get invite buttons in DM\n"
                "• `/translate <text> <target>` — translate manually\n"
                "• `/setmylang <code>` — set your personal language\n"
                "• `/langlist` — show supported languages\n"
                "• `/leaderboard` — top translators in this server\n"
                "• `/ping` — latency test\n"
            )
        )
        e.set_footer(text=footer())
        await it.response.edit_message(embed=e, view=self)

    @discord.ui.button(label="Admin", emoji=Z_CONFUSED, style=discord.ButtonStyle.secondary)
    async def tab_admin(self, it: discord.Interaction, btn: discord.ui.Button):
        if not self.is_admin:
            return await it.response.send_message("You need Administrator permissions.", ephemeral=True)
        e = discord.Embed(
            title="Admin Commands",
            color=COLOR,
            description=(
                "• `/defaultlang <code>` — set server default language\n"
                "• `/channelselection` — choose translation channels\n"
                "• `/emote <emoji>` — set bot's reaction emote\n"
                "• `/seterrorchannel <#channel|id|none>` — error logs\n"
                "• `/settings` — show current server settings\n"
                "• `/guide` — post the onboarding guide\n"
                "• `/ops ping|sync|reload|selftest` — diagnostics\n"
            )
        )
        e.set_footer(text=footer())
        await it.response.edit_message(embed=e, view=self)

    @discord.ui.button(label="Owner", emoji=Z_HAPPY, style=discord.ButtonStyle.secondary)
    async def tab_owner(self, it: discord.Interaction, btn: discord.ui.Button):
        if it.user.id != OWNER_ID:
            return await it.response.send_message("Owner only.", ephemeral=True)
        e = discord.Embed(
            title="Owner Commands",
            color=COLOR,
            description=(
                "• `/owner stats` — bot stats (owner view)\n"
                "• `/owner guilds` — list servers\n"
                "• `/ops reload` — hot-reload all cogs\n"
                "• `/ops sync` — resync slash commands\n"
            )
        )
        e.set_footer(text=footer())
        await it.response.edit_message(embed=e, view=self)

class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show Zephyra help.")
    async def help(self, interaction: discord.Interaction):
        is_admin = interaction.user.guild_permissions.administrator if interaction.guild else False
        is_owner = interaction.user.id == OWNER_ID
        e = discord.Embed(title=HELP_TITLE, description=f"{Z_LOVE} Choose a category below.", color=COLOR)
        e.set_footer(text=footer())
        await interaction.response.send_message(embed=e, view=HelpTabs(is_admin, is_owner), ephemeral=True)

    @app_commands.command(name="guide", description="Post an onboarding guide for your members.")
    async def guide(self, interaction: discord.Interaction):
        """Posts a short guide explaining how translation works."""
        await interaction.response.defer()
        desc = (
            "**How Zephyra works**\n\n"
            "1) Admin picks translation channels with `/channelselection`.\n"
            "2) In those channels, Zephyra reacts to every message with your configured emoji.\n"
            "3) Tap that emoji to get a **DM** with the translation to your personal language.\n"
            "   • Set your personal language via `/setmylang <code>` (autocomplete).\n"
            "   • If you didn't set one, the server default from `/defaultlang` is used.\n"
            "4) You can also translate manually with `/translate <text> <target>`.\n"
            "5) Check `/leaderboard` for the most active translators.\n"
        )
        e = discord.Embed(title="Getting Started with Zephyra", description=desc, color=COLOR)
        e.set_footer(text=footer())
        await interaction.followup.send(embed=e)

    @app_commands.command(name="setmylang", description="Set your personal translation language.")
    @app_commands.autocomplete(lang=ac_lang)
    async def setmylang(self, interaction: discord.Interaction, lang: str):
        await interaction.response.defer(ephemeral=True)
        lang = (lang or "").lower().strip()
        if lang not in codes():
            e = discord.Embed(description=f"Unsupported language code `{lang}`.", color=COLOR)
            e.set_footer(text=footer())
            return await interaction.followup.send(embed=e, ephemeral=True)
        await database.set_user_lang(interaction.user.id, lang)
        e = discord.Embed(description=f"✅ Your language is now {label(lang)}.", color=COLOR)
        e.set_footer(text=footer())
        await interaction.followup.send(embed=e, ephemeral=True)

    @app_commands.command(name="langlist", description="Show all supported languages.")
    async def langlist(self, interaction: discord.Interaction):
        chunks, cur = [], []
        for i, l in enumerate(SUPPORTED_LANGUAGES, start=1):
            cur.append(f'{l["flag"]} `{l["code"]}` {l["name"]}')
            if i % 3 == 0:
                chunks.append("   |   ".join(cur)); cur = []
        if cur:
            chunks.append("   |   ".join(cur))
        e = discord.Embed(title="🌐 Supported Languages", description="\n".join(chunks), color=COLOR)
        e.set_footer(text=footer())
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="ping", description="Show latency.")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Pong! `{round(self.bot.latency * 1000)} ms`", ephemeral=True)

async def setup(bot):
    await bot.add_cog(UserCommands(bot))
