# cogs/user_commands.py
import discord
from discord.ext import commands
from discord import app_commands
from utils import database

BOT_COLOR = 0xDE002A
OWNER_ID = 762267166031609858  # Polarix

LANG_CATALOG = [
    ("en","🇬🇧","English"), ("de","🇩🇪","German"), ("fr","🇫🇷","French"), ("es","🇪🇸","Spanish"),
    ("it","🇮🇹","Italian"), ("pt","🇵🇹","Portuguese"), ("ru","🇷🇺","Russian"), ("zh","🇨🇳","Chinese"),
    ("ja","🇯🇵","Japanese"), ("ko","🇰🇷","Korean"), ("ar","🇸🇦","Arabic"), ("tr","🇹🇷","Turkish"),
    ("nl","🇳🇱","Dutch"), ("sv","🇸🇪","Swedish"), ("no","🇳🇴","Norwegian"), ("da","🇩🇰","Danish"),
    ("fi","🇫🇮","Finnish"), ("pl","🇵🇱","Polish"), ("cs","🇨🇿","Czech"), ("el","🇬🇷","Greek"),
    ("uk","🇺🇦","Ukrainian"), ("he","🇮🇱","Hebrew"), ("vi","🇻🇳","Vietnamese"), ("th","🇹🇭","Thai"),
    ("id","🇮🇩","Indonesian"), ("ms","🇲🇾","Malay"), ("fa","🇮🇷","Persian"), ("sw","🇰🇪","Swahili"),
    ("am","🇪🇹","Amharic"), ("yo","🇳🇬","Yoruba"), ("ha","🇳🇬","Hausa"),
]
SUPPORTED = {c for c,_,_ in LANG_CATALOG}

def _choices(q: str):
    q = (q or "").lower().strip()
    vals = []
    for code, flag, name in LANG_CATALOG:
        if not q or q in code or q in name.lower():
            vals.append(app_commands.Choice(name=f"{flag} {name} ({code})"[:100], value=code))
        if len(vals) >= 25: break
    return vals or [app_commands.Choice(name=f"{f} {n} ({c})"[:100], value=c)
                    for c,f,n in LANG_CATALOG[:25]]

async def lang_autocomplete(_itx: discord.Interaction, current: str):
    return _choices(current)

class HelpView(discord.ui.View):
    def __init__(self, is_admin: bool, is_owner: bool):
        super().__init__(timeout=120)
        self.is_admin = is_admin
        self.is_owner = is_owner
        # Buttons
        self.add_item(discord.ui.Button(label="General", style=discord.ButtonStyle.primary, custom_id="g"))
        if is_admin:
            self.add_item(discord.ui.Button(label="Admin", style=discord.ButtonStyle.secondary, custom_id="a"))
        if is_owner:
            self.add_item(discord.ui.Button(label="Owner", style=discord.ButtonStyle.secondary, custom_id="o"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True  # allow anyone to switch tabs on the same message

    @discord.ui.button(label="General", style=discord.ButtonStyle.primary)
    async def _g(self, _, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=embed_general(), view=HelpView(
            interaction.user.guild_permissions.administrator,
            interaction.user.id == OWNER_ID
        ))

    @discord.ui.button(label="Admin", style=discord.ButtonStyle.secondary)
    async def _a(self, _, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.defer()
        await interaction.response.edit_message(embed=embed_admin(), view=HelpView(True, interaction.user.id == OWNER_ID))

    @discord.ui.button(label="Owner", style=discord.ButtonStyle.secondary)
    async def _o(self, _, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            return await interaction.response.defer()
        await interaction.response.edit_message(embed=embed_owner(), view=HelpView(
            interaction.user.guild_permissions.administrator, True
        ))

def embed_general():
    e = discord.Embed(title="🤝 User Commands", color=BOT_COLOR, description=(
        "• `/setmylang` — choose your language (autocomplete)\n"
        "• `/translate <text> <lang>` — manual translation (autocomplete)\n"
        "• `/ping` — latency\n"
        "• `/help` — open this menu\n"
        "• `/langlist` — language codes\n"
        "• `/leaderboard` — top translators"
    ))
    return e

def embed_admin():
    e = discord.Embed(title="🛠️ Admin Commands", color=BOT_COLOR, description=(
        "• `/defaultlang <lang>` — set server default (autocomplete)\n"
        "• `/channelselection` — select translation channels\n"
        "• `/emote <emoji>` — set reaction emoji (falls back to 🔁 if invalid)\n"
        "• `/seterrorchannel <#chan|none>` — error logs\n"
        "• `/librestatus` — check Libre/Argos health\n"
        "• `/stats` — bot stats & AI usage\n"
        "• `/guide` — send the welcome guide embed"
    ))
    return e

def embed_owner():
    e = discord.Embed(title="👑 Owner Commands", color=BOT_COLOR, description=(
        "• `/reload` — reload cogs\n"
        "• `/backup` — backup DB\n"
        "• `/summonpolarix` — DM your invite link button"
    ))
    return e

class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show commands (User/Admin/Owner).")
    async def help(self, interaction: discord.Interaction):
        is_admin = interaction.user.guild_permissions.administrator if interaction.guild else False
        is_owner = interaction.user.id == OWNER_ID
        await interaction.response.send_message(embed=embed_general(), view=HelpView(is_admin, is_owner), ephemeral=True)

    @app_commands.command(name="guide", description="(Admin) Post the server guide embed.")
    @app_commands.checks.has_permissions(administrator=True)
    async def guide(self, interaction: discord.Interaction):
        e = discord.Embed(
            title="👋 Welcome to Demon Translator",
            description=(
                "✅ React with the bot's emoji to receive a DM translation.\n"
                "✅ Set your language with `/setmylang` (clean dropdown).\n"
                "✅ Translate any text with `/translate <text>`.\n"
                "ℹ️ Use `/help` anytime for a full command menu."
            ),
            color=BOT_COLOR
        )
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Invite Me", url="https://discord.com/api/oauth2/authorize?client_id=1425590836800000170&permissions=2147483648&scope=bot%20applications.commands"))
        await interaction.response.send_message(embed=e, view=view)

    @app_commands.command(name="ping", description="Check latency.")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Pong! `{round(interaction.client.latency*1000)}ms`", ephemeral=True)

    @app_commands.autocomplete(lang=lang_autocomplete)
    @app_commands.command(name="setmylang", description="Set your personal translation language.")
    async def setmylang(self, interaction: discord.Interaction, lang: str):
        lang = lang.lower()
        if lang not in SUPPORTED:
            return await interaction.response.send_message("❌ Invalid language code.", ephemeral=True)
        await database.set_user_lang(interaction.user.id, lang)
        await interaction.response.send_message(f"✅ Your language is now `{lang}`.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(UserCommands(bot))