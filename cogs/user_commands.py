# cogs/user_commands.py
import discord
from discord.ext import commands
from discord import app_commands
from utils.brand import NAME, COLOR, HELP_TITLE, FOOTER
from cogs.translate import SUPPORTED_LANGS, LANG_LOOKUP, _filter_lang_choices

def embed_general() -> discord.Embed:
    e = discord.Embed(
        title=HELP_TITLE,
        description=(
            "**Commands for everyone**\n"
            "• `/translate <text> <target_lang>` — translate text.\n"
            "• `/setmylang <lang>` — set your personal target language.\n"
            "• `/langlist` — show supported languages.\n"
            "• `/invite` — DM yourself an invite button.\n"
            "• `/ping` — latency and health.\n"
            "• `/help` — open this menu.\n"
        ),
        color=COLOR
    )
    e.set_footer(text=FOOTER)
    return e

def embed_admin() -> discord.Embed:
    e = discord.Embed(
        title="Admin Tools",
        description=(
            "**Setup & Control**\n"
            "• `/channelselection` — select channels for reaction-based translation.\n"
            "• `/defaultlang <lang>` — set server default language.\n"
            "• `/aisettings <true|false>` — enable AI fallback.\n"
            "• `/settings` — show server config.\n"
            "• `/librestatus` — check Libre endpoint.\n"
            "• `/stats` — usage & counters.\n"
            "• `/leaderboard` — top translators.\n"
            "• `/guide` — post the quick-start guide.\n"
        ),
        color=COLOR
    )
    e.set_footer(text=FOOTER)
    return e

def embed_owner() -> discord.Embed:
    e = discord.Embed(
        title="Owner Tools",
        description=(
            "**Maintenance**\n"
            "• `/reload` — hot-reload all cogs.\n"
            "• `/backup` — DM database backup.\n"
            "• `/selftest` — full health check.\n"
        ),
        color=COLOR
    )
    e.set_footer(text=FOOTER)
    return e

class HelpView(discord.ui.View):
    def __init__(self, is_admin: bool, is_owner: bool):
        super().__init__(timeout=120)
        self.add_item(self._btn("General", embed_general(), primary=True))
        self.add_item(self._btn("Admin",   embed_admin(),   disabled=not is_admin))
        self.add_item(self._btn("Owner",   embed_owner(),   disabled=not is_owner))

    def _btn(self, label: str, embed: discord.Embed, primary=False, disabled=False):
        style = discord.ButtonStyle.primary if primary else discord.ButtonStyle.secondary
        b = discord.ui.Button(label=label, style=style, disabled=disabled)
        async def cb(it: discord.Interaction):
            await it.response.edit_message(embed=embed, view=self)
        b.callback = cb
        return b

# ---------- Autocomplete (must be async) ----------
async def user_lang_autocomplete(_interaction: discord.Interaction, current: str):
    return _filter_lang_choices(current)

class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description=f"Show {NAME}'s help menu.")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        is_admin = bool(interaction.guild and interaction.user.guild_permissions.administrator)
        is_owner = (interaction.user.id == 762267166031609858)
        await interaction.followup.send(embed=embed_general(), view=HelpView(is_admin, is_owner), ephemeral=True)

    @app_commands.command(name="ping", description="Check latency and health.")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        ws = round(self.bot.latency * 1000)
        await interaction.followup.send(f"Pong. WebSocket latency: **{ws}ms**", ephemeral=True)

    @app_commands.autocomplete(lang=user_lang_autocomplete)
    @app_commands.command(name="setmylang", description="Set your personal translation language.")
    async def setmylang(self, interaction: discord.Interaction, lang: str):
        await interaction.response.defer(ephemeral=True)
        code = lang.lower()
        if code not in SUPPORTED_LANGS:
            return await interaction.followup.send("❌ Unsupported language. Please use the suggestions.", ephemeral=True)
        from utils import database
        await database.set_user_lang(interaction.user.id, code)
        flag, name = LANG_LOOKUP.get(code, ("🏳️", code))
        await interaction.followup.send(f"Your language is now **{name} ({code}) {flag}**.", ephemeral=True)

    @app_commands.command(name="langlist", description="Show supported languages.")
    async def langlist(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        rows, line = [], []
        for code in sorted(LANG_LOOKUP.keys()):
            flag, name = LANG_LOOKUP[code]
            line.append(f"{flag} `{code}` {name}")
            if len(line) == 3:
                rows.append("   |   ".join(line)); line = []
        if line:
            rows.append("   |   ".join(line))
        embed = discord.Embed(title=f"{NAME} Languages", description="\n".join(rows), color=COLOR)
        embed.set_footer(text=FOOTER)
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(UserCommands(bot))
