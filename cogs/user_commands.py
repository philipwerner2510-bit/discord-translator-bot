# cogs/user_commands.py
import os
import discord
from discord.ext import commands
from discord import app_commands
from utils import database
from utils.config import SUPPORTED_LANGS, LANG_META, lang_label

OWNER_ID = int(os.getenv("OWNER_ID", "762267166031609858"))  # Polarix1954


def pretty_lang(code: str | None) -> str:
    if not code:
        return "—"
    flag, name = LANG_META.get(code, ("🌐", code.upper()))
    return f"{flag} {name} ({code})"


class HelpView(discord.ui.View):
    """Tabbed /help with permission-aware buttons and dynamic content."""
    def __init__(self, interaction: discord.Interaction, user_lang: str | None, server_lang: str | None):
        super().__init__(timeout=120)
        self._invoker = interaction.user
        self._guild = interaction.guild
        self._is_admin = bool(self._guild and self._invoker.guild_permissions.administrator)
        self._is_owner = self._invoker.id == OWNER_ID
        self._user_lang = user_lang
        self._server_lang = server_lang

        # Disable tabs the user cannot open
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.label == "Admin" and not self._is_admin:
                    child.disabled = True
                if child.label == "Owner" and not self._is_owner:
                    child.disabled = True

    async def _swap(self, itx: discord.Interaction, embed_builder):
        if itx.user.id != self._invoker.id:
            return await itx.response.defer()
        await itx.response.edit_message(embed=embed_builder(self._user_lang, self._server_lang), view=self)

    @discord.ui.button(label="General", style=discord.ButtonStyle.primary)
    async def btn_general(self, itx: discord.Interaction, button: discord.ui.Button):
        await self._swap(itx, embed_general)

    @discord.ui.button(label="Admin", style=discord.ButtonStyle.secondary)
    async def btn_admin(self, itx: discord.Interaction, button: discord.ui.Button):
        if not self._is_admin:
            return await itx.response.defer()
        await self._swap(itx, embed_admin)

    @discord.ui.button(label="Owner", style=discord.ButtonStyle.danger)
    async def btn_owner(self, itx: discord.Interaction, button: discord.ui.Button):
        if not self._is_owner:
            return await itx.response.defer()
        await self._swap(itx, embed_owner)


# ---------- EMBEDS ----------
def embed_general(user_lang: str | None, server_lang: str | None):
    e = discord.Embed(title="📖 Demon Translator — General", color=0xDE002A)
    e.add_field(
        name="/setmylang `[lang]`",
        value=(
            "Set **your** personal language.\n"
            "• Type a code (e.g., `en`, `de`) **or** run `/setmylang` with **no value** to open a dropdown with flags.\n"
            f"• Yours: **{pretty_lang(user_lang)}**"
        ),
        inline=False
    )
    e.add_field(
        name="/translate `<text>` `<lang>`",
        value="Translate any text manually to a target language.",
        inline=False
    )
    e.add_field(name="/langlist", value="Show supported languages (flags + names + codes).", inline=False)
    e.add_field(name="/leaderboard", value="Top translators (global).", inline=False)
    e.add_field(name="/mystats", value="Your translation count in this server.", inline=False)
    e.add_field(name="/guildstats", value="Total translations in this server.", inline=False)
    e.add_field(name="/test", value="Quick responsiveness check.", inline=False)
    e.add_field(name="/ping", value="Show bot latency (ms).", inline=False)
    e.set_footer(text=f"Server default language: {pretty_lang(server_lang)} • Created by Polarix1954")
    return e


def embed_admin(_user_lang: str | None, server_lang: str | None):
    e = discord.Embed(title="🛠 Admin Commands", description="Administrator permissions required.", color=0xDE002A)
    e.add_field(
        name="/defaultlang `[lang]`",
        value=(
            "Set **server default** language.\n"
            "• Type a code **or** run `/defaultlang` with **no value** to open a dropdown with flags.\n"
            f"• Current server default: **{pretty_lang(server_lang)}**"
        ),
        inline=False
    )
    e.add_field(name="/channelselection", value="Pick channels where the bot reacts for translation.", inline=False)
    e.add_field(name="/seterrorchannel `<#channel|none>`", value="Set or clear the error logging channel.", inline=False)
    e.add_field(name="/emote `<emoji>`", value="Set the trigger emoji (unicode or custom).", inline=False)
    e.add_field(name="/settings", value="View server settings.", inline=False)
    e.add_field(name="/config", value="Show bot config & wiring (paths, counts).", inline=False)
    e.add_field(name="/stats", value="Uptime, servers, translations today.", inline=False)
    return e


def embed_owner(_user_lang: str | None, _server_lang: str | None):
    e = discord.Embed(title="👑 Owner Commands", description="Reserved for Polarix1954", color=0xDE002A)
    e.add_field(name="/reloadconfig", value="Reload `config.json` without a restart.", inline=False)
    e.add_field(name="/exportdb", value="Export a live DB backup to `/mnt/data`.", inline=False)
    return e


# ---------- COG ----------
class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # /help (permission-aware tabs + dynamic info)
    @app_commands.command(name="help", description="Show help for Demon Translator.")
    async def help_cmd(self, interaction: discord.Interaction):
        # Load user/server context for dynamic help
        user_lang = await database.get_user_lang(interaction.user.id)
        server_lang = await database.get_server_lang(interaction.guild.id) if interaction.guild else None

        view = HelpView(interaction, user_lang, server_lang)
        await interaction.response.send_message(
            embed=embed_general(user_lang, server_lang),
            view=view,
            ephemeral=True
        )

    # /test
    @app_commands.command(name="test", description="Check if the bot is responsive.")
    async def test_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Demon Bot is online and lurking 😈", ephemeral=True)

    # /ping
    @app_commands.command(name="ping", description="Check bot latency.")
    async def ping_cmd(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"🏓 Pong! `{latency}ms`", ephemeral=True)

    # /setmylang — typed OR dropdown (no-arg)
    @app_commands.command(name="setmylang", description="Set your personal translation language.")
    @app_commands.describe(lang="Language code (e.g., en, de). Leave empty to pick from a dropdown.")
    async def setmylang(self, interaction: discord.Interaction, lang: str | None = None):
        if lang:
            code = lang.lower()
            if code not in SUPPORTED_LANGS:
                return await interaction.response.send_message(
                    f"❌ Unsupported: `{code}`. Try `/langlist` or run `/setmylang` without a value to pick from a list.",
                    ephemeral=True
                )
            await database.set_user_lang(interaction.user.id, code)
            return await interaction.response.send_message(f"✅ Saved your language as **{pretty_lang(code)}**", ephemeral=True)

        # open dropdown
        PER_PAGE = 25
        codes_sorted = sorted(SUPPORTED_LANGS, key=lambda c: LANG_META.get(c, ("🌐", c.upper()))[1])
        pages = [codes_sorted[i:i+PER_PAGE] for i in range(0, len(codes_sorted), PER_PAGE)]
        total_pages = len(pages)

        class PickerView(discord.ui.View):
            def __init__(self, user: discord.User, page_idx: int = 0):
                super().__init__(timeout=60)
                self.user = user
                self.page_idx = page_idx
                self._rebuild()

            def _rebuild(self):
                self.clear_items()
                current = pages[self.page_idx]
                options = [
                    discord.SelectOption(label=lang_label(code)[:100], value=code, description=f"Code: {code}")
                    for code in current
                ]
                select = discord.ui.Select(
                    placeholder=f"Choose your language — Page {self.page_idx+1}/{total_pages}",
                    min_values=1, max_values=1, options=options
                )

                async def on_select(itx: discord.Interaction):
                    if itx.user.id != self.user.id:
                        return await itx.response.defer()
                    code = select.values[0]
                    await database.set_user_lang(self.user.id, code)
                    await itx.response.edit_message(content=f"✅ Saved your language as **{pretty_lang(code)}**", view=None)
                    self.stop()

                select.callback = on_select
                self.add_item(select)

                if total_pages > 1:
                    @discord.ui.button(label="⬅ Previous", style=discord.ButtonStyle.secondary, disabled=self.page_idx == 0)
                    async def prev_btn(itx: discord.Interaction, button: discord.ui.Button):
                        if itx.user.id != self.user.id:
                            return await itx.response.defer()
                        self.page_idx -= 1
                        self._rebuild()
                        await itx.response.edit_message(content=self._content(), view=self)

                    @discord.ui.button(label="Next ➡", style=discord.ButtonStyle.primary, disabled=self.page_idx >= total_pages - 1)
                    async def next_btn(itx: discord.Interaction, button: discord.ui.Button):
                        if itx.user.id != self.user.id:
                            return await itx.response.defer()
                        self.page_idx += 1
                        self._rebuild()
                        await itx.response.edit_message(content=self._content(), view=self)

            def _content(self):
                return "Pick your personal translation language 👇"

        view = PickerView(interaction.user)
        await interaction.response.send_message(content=view._content(), view=view, ephemeral=True)

    @setmylang.autocomplete("lang")
    async def _auto_lang(self, interaction: discord.Interaction, current: str):
        cur = (current or "").lower()
        matches = [c for c in SUPPORTED_LANGS if cur in c or cur in LANG_META.get(c, ("", ""))[1].lower()]
        return [app_commands.Choice(name=lang_label(c)[:100], value=c) for c in matches[:25]]

    # (Optional stub so users see /translate in help even if they try it here)
    @app_commands.command(name="translate", description="Translate a specific text manually.")
    async def translate_stub(self, interaction: discord.Interaction, text: str, lang: str):
        await interaction.response.send_message(
            "Heads up: use the main **/translate** command (enabled in this server).",
            ephemeral=True
        )

    @app_commands.command(name="mystats", description="Your translation count.")
    async def mystats(self, interaction: discord.Interaction):
        count = await database.get_user_count(interaction.user.id)
        await interaction.response.send_message(f"📊 You translated `{count}` messages.", ephemeral=True)

    @app_commands.command(name="leaderboard", description="Top translators globally.")
    async def leaderboard(self, interaction: discord.Interaction):
        data = await database.get_top_users(10)
        if not data:
            return await interaction.response.send_message("📭 No stats yet.", ephemeral=True)
        desc = "\n".join([f"**<@{uid}>** — `{count}`" for uid, count in data])
        embed = discord.Embed(title="🌍 Global Leaderboard", description=desc, color=0xDE002A)
        await interaction.response.send_message(embed=embed)

    @app_commands.guild_only()
    @app_commands.command(name="guildstats", description="Server translation stats.")
    async def guildstats(self, interaction: discord.Interaction):
        count = await database.get_guild_count(interaction.guild.id)
        await interaction.response.send_message(f"📈 This server translated `{count}` messages.")

async def setup(bot):
    await bot.add_cog(UserCommands(bot))