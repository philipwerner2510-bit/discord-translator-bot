# cogs/user_commands.py
import os
import discord
from discord.ext import commands
from discord import app_commands

BOT_COLOR = 0xDE002A
OWNER_ID = 762267166031609858  # Polarix1954

def build_invite_url(app_id: int) -> str:
    # Permissions: Send Messages, Embed Links, Read Message History, Add Reactions, Use App Commands, etc.
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


# ---------- Help Embeds ----------
def embed_user() -> discord.Embed:
    e = discord.Embed(
        title="👋 Demon Translator — User Guide",
        color=BOT_COLOR,
        description=(
            "Welcome! Here’s how to use me:\n\n"
            "• **React** to any message with the bot emote to get a DM with the translation.\n"
            "• Set your personal language with **/setmylang** (clean dropdown menu).\n"
            "• Translate any text directly using **/translate <text>**.\n"
            "• Check connectivity with **/ping**.\n"
        )
    )
    e.add_field(
        name="User Commands",
        value=(
            "• `/setmylang` — choose your language (dropdown)\n"
            "• `/translate <text>` — translate custom text\n"
            "• `/langlist` — show supported language codes\n"
            "• `/ping` — check bot latency\n"
            "• `/help` — open this panel"
        ),
        inline=False
    )
    e.set_footer(text="Demon Translator © by Polarix1954 😈🔥")
    return e

def embed_admin() -> discord.Embed:
    e = discord.Embed(
        title="🛠️ Demon Translator — Admin Guide",
        color=BOT_COLOR,
        description=(
            "Admin tools to configure the bot in your server.\n"
            "You need **Administrator** permission to use these."
        )
    )
    e.add_field(
        name="Setup",
        value=(
            "• `/channelselection` — pick channels where reactions trigger translations\n"
            "• `/defaultlang <code>` — set server default language (e.g. `en`, `de`)\n"
            "• `/emote <emote>` — set the reaction emote the bot listens for\n"
            "• `/seterrorchannel #channel` — receive warnings & errors"
        ),
        inline=False
    )
    e.add_field(
        name="Management",
        value=(
            "• `/settings` — view current configuration (with quick tools)\n"
            "• `/aisettings <true|false>` — enable/disable advanced translation\n"
            "• `/librestatus` — status check for the translation endpoint\n"
            "• `/langlist` — show supported language codes"
        ),
        inline=False
    )
    e.set_footer(text="Tip: Use /settings for quick tests & health checks.")
    return e

def embed_owner() -> discord.Embed:
    e = discord.Embed(
        title="👑 Demon Translator — Owner Panel",
        color=BOT_COLOR,
        description="Private controls for the bot owner."
    )
    e.add_field(
        name="Owner Commands",
        value=(
            "• `/stats` — live counters (cache, usage, cost, uptime)\n"
            "• `/aitest` — quick translation demo\n"
            "• `/ping` — latency check"
        ),
        inline=False
    )
    e.set_footer(text="Owner: Polarix1954")
    return e


# ---------- Help View with Tabs ----------
class HelpView(discord.ui.View):
    def __init__(self, *, show_owner: bool, invite_url: str):
        super().__init__(timeout=120)
        self.invite_url = invite_url

        # Tab buttons
        self.add_item(self.UserTab())
        self.add_item(self.AdminTab())
        if show_owner:
            self.add_item(self.OwnerTab())

        # Invite link (always visible)
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

    # -----------------------
    # /help — with tabbed view (User/Admin/Owner)
    # -----------------------
    @app_commands.command(name="help", description="Interactive help: User, Admin, and Owner tabs.")
    async def help_cmd(self, interaction: discord.Interaction):
        app_id = self.bot.user.id if self.bot.user else 0
        invite_url = build_invite_url(app_id)
        show_owner = (interaction.user.id == OWNER_ID)

        await interaction.response.send_message(
            embed=embed_user(),  # default to User tab
            view=HelpView(show_owner=show_owner, invite_url=invite_url),
            ephemeral=True
        )

    # -----------------------
    # /ping — latency check
    # -----------------------
    @app_commands.command(name="ping", description="Check bot latency.")
    async def ping_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"🏓 Pong! {round(self.bot.latency * 1000)}ms", ephemeral=True)

    # -----------------------
    # /aitest — owner-only quick demo
    # -----------------------
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
                    model="gpt-4o-mini",
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