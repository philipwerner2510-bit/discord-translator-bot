import discord
from discord.ext import commands
from discord import app_commands
from utils import database

BOT_COLOR = 0xDE002A
OWNER_ID = 762267166031609858

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
    vals=[]
    for code, flag, name in LANG_CATALOG:
        if not q or q in code or q in name.lower():
            vals.append(app_commands.Choice(name=f"{flag} {name} ({code})"[:100], value=code))
        if len(vals) >= 25: break
    return vals or [app_commands.Choice(name=f"{f} {n} ({c})"[:100], value=c)
                    for c,f,n in LANG_CATALOG[:25]]

async def lang_autocomplete(_itx: discord.Interaction, current: str):
    return _choices(current)

def embed_general():
    return discord.Embed(
        title="🤝 User Commands",
        description=(
            "• **/setmylang** — choose your language (autocomplete)\n"
            "• **/translate &lt;text&gt; &lt;lang&gt;** — manual translate (autocomplete)\n"
            "• **/ping** — latency\n"
            "• **/help** — open this menu\n"
            "• **/langlist** — language codes\n"
            "• **/leaderboard** — top translators"
        ),
        color=BOT_COLOR
    )

def embed_admin():
    return discord.Embed(
        title="🛠️ Admin Commands",
        description=(
            "• **/defaultlang &lt;lang&gt;** — set server default (autocomplete)\n"
            "• **/channelselection** — choose translation channels\n"
            "• **/emote &lt;emoji&gt;** — reaction emoji (falls back to 🔁)\n"
            "• **/seterrorchannel &lt;#chan|none&gt;** — error logs\n"
            "• **/librestatus** — check Libre/Argos health\n"
            "• **/stats** — bot stats & AI usage\n"
            "• **/guide** — post welcome guide"
        ),
        color=BOT_COLOR
    )

def embed_owner():
    return discord.Embed(
        title="👑 Owner Commands",
        description=(
            "• **/reload** — reload cogs\n"
            "• **/backup** — backup DB\n"
            "• **/summonpolarix** — DM invite link button"
        ),
        color=BOT_COLOR
    )

class HelpView(discord.ui.View):
    def __init__(self, is_admin: bool, is_owner: bool):
        super().__init__(timeout=120)
        # build buttons dynamically (no decorator = no duplicates)
        btn_g = discord.ui.Button(label="General", style=discord.ButtonStyle.primary)
        async def cb_g(interaction: discord.Interaction):
            await interaction.response.edit_message(embed=embed_general(), view=HelpView(
                interaction.user.guild_permissions.administrator if interaction.guild else False,
                interaction.user.id == OWNER_ID
            ))
        btn_g.callback = cb_g
        self.add_item(btn_g)

        if is_admin:
            btn_a = discord.ui.Button(label="Admin", style=discord.ButtonStyle.secondary)
            async def cb_a(interaction: discord.Interaction):
                if not (interaction.guild and interaction.user.guild_permissions.administrator):
                    return await interaction.response.defer()
                await interaction.response.edit_message(embed=embed_admin(), view=HelpView(True, interaction.user.id == OWNER_ID))
            btn_a.callback = cb_a
            self.add_item(btn_a)

        if is_owner:
            btn_o = discord.ui.Button(label="Owner", style=discord.ButtonStyle.secondary)
            async def cb_o(interaction: discord.Interaction):
                if interaction.user.id != OWNER_ID:
                    return await interaction.response.defer()
                await interaction.response.edit_message(embed=embed_owner(), view=HelpView(
                    interaction.user.guild_permissions.administrator if interaction.guild else False,
                    True
                ))
            btn_o.callback = cb_o
            self.add_item(btn_o)

class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show commands (User/Admin/Owner).")
    async def help(self, interaction: discord.Interaction):
        is_admin = interaction.user.guild_permissions.administrator if interaction.guild else False
        is_owner = interaction.user.id == OWNER_ID
        await interaction.response.send_message(embed=embed_general(), view=HelpView(is_admin, is_owner), ephemeral=True)

    @app_commands.command(name="guide", description="(Admin) Send the onboarding guide embed.")
    @app_commands.checks.has_permissions(administrator=True)
    async def guide(self, interaction: discord.Interaction):
        e = discord.Embed(
            title="👋 Welcome to Demon Translator",
            description=(
                "✅ React with the bot's emoji to receive a DM translation.\n"
                "✅ Set your language with `/setmylang` (autocomplete).\n"
                "✅ Translate any text with `/translate <text>`.\n"
                "ℹ️ Use `/help` anytime for a full command menu."
            ),
            color=BOT_COLOR
        )
        await interaction.response.send_message(embed=e)

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

    @app_commands.command(name="langlist", description="Show supported language codes.")
    async def langlist(self, interaction: discord.Interaction):
        rows=[]
        for i,(code,flag,name) in enumerate(LANG_CATALOG,1):
            rows.append(f"{flag} `{code}` {name}")
        e = discord.Embed(title="🌐 Supported Languages", description="\n".join(rows), color=BOT_COLOR)
        e.set_footer(text=f"Total: {len(LANG_CATALOG)}")
        await interaction.response.send_message(embed=e, ephemeral=True)

async def setup(bot):
    await bot.add_cog(UserCommands(bot))