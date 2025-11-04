# cogs/user_commands.py
import os
import math
import discord
from discord.ext import commands
from discord import app_commands

BOT_COLOR = 0xDE002A
OWNER_ID = 762267166031609858  # Polarix1954

# === 50+ Global Languages (code -> (flag, name)) ===
LANG_CATALOG = [
    ("en","🇬🇧","English"), ("de","🇩🇪","German"), ("fr","🇫🇷","French"), ("es","🇪🇸","Spanish"),
    ("it","🇮🇹","Italian"), ("pt","🇵🇹","Portuguese"), ("ru","🇷🇺","Russian"), ("zh","🇨🇳","Chinese"),
    ("ja","🇯🇵","Japanese"), ("ko","🇰🇷","Korean"), ("ar","🇸🇦","Arabic"), ("tr","🇹🇷","Turkish"),
    ("nl","🇳🇱","Dutch"), ("sv","🇸🇪","Swedish"), ("no","🇳🇴","Norwegian"), ("da","🇩🇰","Danish"),
    ("fi","🇫🇮","Finnish"), ("pl","🇵🇱","Polish"), ("cs","🇨🇿","Czech"), ("sk","🇸🇰","Slovak"),
    ("hu","🇭🇺","Hungarian"), ("ro","🇷🇴","Romanian"), ("bg","🇧🇬","Bulgarian"), ("el","🇬🇷","Greek"),
    ("uk","🇺🇦","Ukrainian"), ("he","🇮🇱","Hebrew"), ("hi","🇮🇳","Hindi"), ("bn","🇧🇩","Bengali"),
    ("ta","🇮🇳","Tamil"), ("te","🇮🇳","Telugu"), ("mr","🇮🇳","Marathi"), ("gu","🇮🇳","Gujarati"),
    ("pa","🇮🇳","Punjabi"), ("ur","🇵🇰","Urdu"), ("vi","🇻🇳","Vietnamese"), ("th","🇹🇭","Thai"),
    ("id","🇮🇩","Indonesian"), ("ms","🇲🇾","Malay"), ("fa","🇮🇷","Persian"), ("sw","🇰🇪","Swahili"),
    ("am","🇪🇹","Amharic"), ("yo","🇳🇬","Yoruba"), ("ha","🇳🇬","Hausa"), ("az","🇦🇿","Azerbaijani"),
    ("ka","🇬🇪","Georgian"), ("et","🇪🇪","Estonian"), ("lv","🇱🇻","Latvian"), ("lt","🇱🇹","Lithuanian"),
    ("sr","🇷🇸","Serbian"), ("hr","🇭🇷","Croatian"), ("sl","🇸🇮","Slovenian"), ("ga","🇮🇪","Irish"),
    ("is","🇮🇸","Icelandic"), ("mt","🇲🇹","Maltese"), ("af","🇿🇦","Afrikaans"), ("zu","🇿🇦","Zulu"),
    ("xh","🇿🇦","Xhosa"), ("fil","🇵🇭","Filipino"),
]
LANG_INDEX = {code:(flag,name) for code,flag,name in LANG_CATALOG}

def build_invite_url(app_id: int) -> str:
    perms = 274878188544
    return f"https://discord.com/oauth2/authorize?client_id={app_id}&permissions={perms}&scope=bot%20applications.commands"

# ---------- Optional: lazy OpenAI client for /aitest ----------
from openai import OpenAI
_oai_client = None
def get_oai_client():
    global _oai_client
    if _oai_client is None:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            return None
        try:
            _oai_client = OpenAI(api_key=key)
        except Exception:
            _oai_client = None
    return _oai_client


# ---------- Embeds (polished & structured) ----------
def embed_user() -> discord.Embed:
    e = discord.Embed(
        title="👋 Demon Translator — User Guide",
        color=BOT_COLOR,
        description=(
            "**Quick Start**\n"
            "1) React to any message with the bot emote to receive a translation.\n"
            "2) Set your language once with **/setmylang** (dropdown).\n"
            "3) Use **/translate <text>** for custom text.\n"
        ),
    )
    e.add_field(
        name="Commands (Users)",
        value=(
            "• `/setmylang` — choose your language (dropdown w/ pages)\n"
            "• `/translate <text>` — translate custom text\n"
            "• `/langlist` — list of top language codes\n"
            "• `/ping` — latency check\n"
            "• `/help` — open this menu\n"
            "• `/guide` — public guide embed (admins send it)"
        ),
        inline=False,
    )
    e.add_field(
        name="Tips",
        value=(
            "• If your DMs are closed, the bot replies in the channel.\n"
            "• You can change your language anytime with `/setmylang`.\n"
            "• Ask an admin to set channels where the bot should react."
        ),
        inline=False,
    )
    e.set_footer(text="Demon Translator © by Polarix1954 😈🔥")
    return e

def embed_admin() -> discord.Embed:
    e = discord.Embed(
        title="🛠️ Demon Translator — Admin Panel",
        color=BOT_COLOR,
        description="Admin tools to configure the bot for your server.",
    )
    e.add_field(
        name="Setup",
        value=(
            "• `/channelselection` — choose channels for reaction-to-translate\n"
            "• `/defaultlang` — set server default language (dropdown w/ pages)\n"
            "• `/emote <emote>` — set the reaction emote the bot listens for\n"
            "• `/seterrorchannel #channel` — receive warnings & errors"
        ),
        inline=False,
    )
    e.add_field(
        name="Management & Diagnostics",
        value=(
            "• `/settings` — view config (with **Test AI** & **Ping Libre** buttons)\n"
            "• `/aisettings <true|false>` — enable/disable advanced translation\n"
            "• `/librestatus` — check translation endpoint health\n"
            "• `/guide` — send the public user guide embed in this channel"
        ),
        inline=False,
    )
    e.add_field(
        name="Good to Know",
        value=(
            "• Users trigger translations by reacting in the selected channels.\n"
            "• Default language applies when a user didn’t set their own.\n"
            "• Error channel is recommended for warnings and health info."
        ),
        inline=False,
    )
    e.set_footer(text="Admins only • Use /settings for quick checks.")
    return e

def embed_owner() -> discord.Embed:
    e = discord.Embed(
        title="👑 Demon Translator — Owner Tools",
        color=BOT_COLOR,
        description="Private controls for the bot owner.",
    )
    e.add_field(
        name="Owner Commands",
        value=(
            "• `/stats` — live counters (cache, usage, cost, uptime)\n"
            "• `/aitest` — quick translation demo\n"
            "• `/ping` — latency check"
        ),
        inline=False,
    )
    e.set_footer(text="Owner: Polarix1954")
    return e


# ---------- Paginated Language Select ----------
MAX_OPTIONS = 25

def page_count(items: list) -> int:
    return max(1, math.ceil(len(items) / MAX_OPTIONS))

def slice_page(items: list, page: int) -> list:
    start = page * MAX_OPTIONS
    end = start + MAX_OPTIONS
    return items[start:end]

class LangSelect(discord.ui.Select):
    def __init__(self, page_items: list[tuple[str,str,str]], placeholder: str):
        options = []
        for code, flag, name in page_items:
            options.append(discord.SelectOption(
                label=f"{flag} {name}",
                value=code,
                description=f"{name} ({code})"
            ))
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)

class LangPager(discord.ui.View):
    def __init__(self, user_id: int, mode: str, guild_id: int | None):
        """
        mode: 'user' or 'server'
        if mode == 'server', only admins can set
        """
        super().__init__(timeout=180)
        self._items = LANG_CATALOG
        self.pages = page_count(self._items)
        self.page = 0
        self.user_id = user_id
        self.mode = mode
        self.guild_id = guild_id
        self._refresh_select()

        # Nav buttons
        self.add_item(self.PrevButton(self))
        self.add_item(self.NextButton(self))

    def _refresh_select(self):
        # Remove any previous selects
        for child in list(self.children):
            if isinstance(child, LangSelect):
                self.remove_item(child)

        # Add current page select
        items = slice_page(self._items, self.page)
        placeholder = "Choose your language…" if self.mode == "user" else "Choose the server default language…"
        select = LangSelect(items, placeholder)
        select.callback = self.on_pick
        self.add_item(select)

    async def on_pick(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This menu isn’t for you.", ephemeral=True)

        code = interaction.data["values"][0]
        flag, name = LANG_INDEX.get(code, ("🏳️","Unknown"))
        if self.mode == "user":
            from utils import database
            await database.set_user_lang(interaction.user.id, code)
            await interaction.response.edit_message(
                content=f"✅ Your personal language is now **{name}** (`{code}`).",
                embed=None, view=None
            )
        else:
            if not interaction.user.guild_permissions.administrator:
                return await interaction.response.send_message("❌ Admins only.", ephemeral=True)
            from utils import database
            await database.set_server_lang(interaction.guild.id, code)
            await interaction.response.edit_message(
                content=f"✅ Server default language is now **{name}** (`{code}`).",
                embed=None, view=None
            )

    class PrevButton(discord.ui.Button):
        def __init__(self, pager: "LangPager"):
            super().__init__(style=discord.ButtonStyle.secondary, label="◀ Prev")
            self.pager = pager
        async def callback(self, interaction: discord.Interaction):
            if interaction.user.id != self.pager.user_id:
                return await interaction.response.send_message("❌ This menu isn’t for you.", ephemeral=True)
            self.pager.page = (self.pager.page - 1) % self.pager.pages
            self.pager._refresh_select()
            await interaction.response.edit_message(view=self.pager)

    class NextButton(discord.ui.Button):
        def __init__(self, pager: "LangPager"):
            super().__init__(style=discord.ButtonStyle.secondary, label="Next ▶")
            self.pager = pager
        async def callback(self, interaction: discord.Interaction):
            if interaction.user.id != self.pager.user_id:
                return await interaction.response.send_message("❌ This menu isn’t for you.", ephemeral=True)
            self.pager.page = (self.pager.page + 1) % self.pager.pages
            self.pager._refresh_select()
            await interaction.response.edit_message(view=self.pager)


# ---------- Help View (User/Admin/Owner tabs) ----------
class HelpView(discord.ui.View):
    def __init__(self, *, show_admin: bool, show_owner: bool, invite_url: str):
        super().__init__(timeout=120)
        self.invite_url = invite_url

        # Always show User
        self.add_item(self.UserTab())

        # Show Admin only for admins
        if show_admin:
            self.add_item(self.AdminTab())

        # Show Owner only for the owner
        if show_owner:
            self.add_item(self.OwnerTab())

        # Invite button (always visible)
        self.add_item(discord.ui.Button(label="➕ Invite Me", style=discord.ButtonStyle.link, url=invite_url))

    class UserTab(discord.ui.Button):
        def __init__(self):
            super().__init__(label="User", style=discord.ButtonStyle.primary)

        async def callback(self, interaction: discord.Interaction):
            await interaction.response.edit_message(embed=embed_user(), view=self.view)

    class AdminTab(discord.ui.Button):
        def __init__(self):
            super().__init__(label="Admin", style=discord.ButtonStyle.secondary)

        async def callback(self, interaction: discord.Interaction):
            await interaction.response.edit_message(embed=embed_admin(), view=self.view)

    class OwnerTab(discord.ui.Button):
        def __init__(self):
            super().__init__(label="Owner", style=discord.ButtonStyle.secondary)

        async def callback(self, interaction: discord.Interaction):
            await interaction.response.edit_message(embed=embed_owner(), view=self.view)


class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # /help — Tabbed view
    @app_commands.command(name="help", description="Interactive help: User, Admin, and Owner tabs.")
    async def help_cmd(self, interaction: discord.Interaction):
        app_id = self.bot.user.id if self.bot.user else 0
        invite_url = build_invite_url(app_id)
        is_owner = (interaction.user.id == OWNER_ID)
        is_admin = bool(interaction.user.guild_permissions.administrator) if interaction.guild else False

        view = HelpView(show_admin=is_admin, show_owner=is_owner, invite_url=invite_url)
        await interaction.response.send_message(embed=embed_user(), view=view, ephemeral=True)

    # /ping
    @app_commands.command(name="ping", description="Check bot latency.")
    async def ping_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"🏓 Pong! {round(self.bot.latency * 1000)}ms", ephemeral=True)

    # /setmylang — paginated dropdown
    @app_commands.command(name="setmylang", description="Choose your personal translation language.")
    async def setmylang(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Pick your language:",
            view=LangPager(user_id=interaction.user.id, mode="user", guild_id=None),
            ephemeral=True
        )

    # /defaultlang — paginated dropdown (admins)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="defaultlang", description="Set the server default translation language.")
    async def defaultlang(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Pick the **server default language**:",
            view=LangPager(user_id=interaction.user.id, mode="server", guild_id=interaction.guild.id),
            ephemeral=True
        )

    # /aitest — owner only
    @app_commands.command(name="aitest", description="Owner-only: quick translation demo.")
    async def aitest_cmd(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            return await interaction.response.send_message("❌ Owner only.", ephemeral=True)

        client = get_oai_client()
        if not client:
            return await interaction.response.send_message("⚠️ No OPENAI_API_KEY set.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        sample = "Nah bro that’s cap, ain’t no way he pulled that W 💀🔥"
        target_lang = "de"

        try:
            resp = await interaction.client.loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    messages=[
                        {"role": "system",
                         "content": f"Translate the user's message to '{target_lang}'. "
                                    f"Preserve tone & emojis. Return only the translation."},
                        {"role": "user", "content": sample},
                    ],
                    temperature=0.2,
                )
            )
            out = resp.choices[0].message.content.strip()
            embed = discord.Embed(
                title="🧪 Demo Result",
                color=BOT_COLOR,
                description=f"**Source:** `{sample}`\n**→ {target_lang.upper()}:** {out}"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Demo failed: `{e}`", ephemeral=True)


async def setup(bot):
    await bot.add_cog(UserCommands(bot))