# cogs/user_commands.py
import discord
from discord.ext import commands
from discord import app_commands
from utils import database
from utils.config import SUPPORTED_LANGS, LANG_META, lang_label

OWNER_ID = 762267166031609858  # Polarix1954


# ---------- HELP VIEW (tabbed) ----------
class HelpView(discord.ui.View):
    def __init__(self, interaction_user):
        super().__init__(timeout=120)
        self.interaction_user = interaction_user

    async def switch(self, interaction, embed_func):
        if interaction.user.id != self.interaction_user.id:
            return await interaction.response.defer()
        await interaction.response.edit_message(embed=embed_func(), view=self)

    @discord.ui.button(label="General", style=discord.ButtonStyle.primary)
    async def general_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch(interaction, embed_general)

    @discord.ui.button(label="Admin", style=discord.ButtonStyle.secondary)
    async def admin_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch(interaction, embed_admin)

    @discord.ui.button(label="Owner", style=discord.ButtonStyle.danger)
    async def owner_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch(interaction, embed_owner)


# ---------- EMBEDS ----------
def embed_general():
    e = discord.Embed(title="📖 Demon Translator – General Commands", color=0xDE002A)
    e.add_field(name="/setmylang `[lang]`", value="Set your personal language. Tip: run **/setmylang** with no value to open a dropdown.", inline=False)
    e.add_field(name="/translate `<text>` `<lang>`", value="Translate any text manually.", inline=False)
    e.add_field(name="/langlist", value="List supported languages (flags + names).", inline=False)
    e.add_field(name="/leaderboard", value="Show top translators.", inline=False)
    e.add_field(name="/mystats", value="Your translation count.", inline=False)
    e.add_field(name="/guildstats", value="Server translation stats.", inline=False)
    e.add_field(name="/test", value="Check if the bot is alive.", inline=False)
    e.add_field(name="/ping", value="Check bot response speed.", inline=False)
    e.set_footer(text="Created by Polarix1954 😈")
    return e


def embed_admin():
    e = discord.Embed(title="🛠 Admin Commands", description="Administrator permissions required.", color=0xDE002A)
    e.add_field(name="/defaultlang `<lang>`", value="Set server default language.", inline=False)
    e.add_field(name="/channelselection", value="Select reaction-enabled channels.", inline=False)
    e.add_field(name="/seterrorchannel", value="Set or remove error channel.", inline=False)
    e.add_field(name="/emote `<emoji>`", value="Set bot reaction emoji.", inline=False)
    e.add_field(name="/settings", value="Show server bot configuration.", inline=False)
    e.add_field(name="/config", value="Show bot configuration overview.", inline=False)
    e.add_field(name="/stats", value="Uptime, servers, translations today.", inline=False)
    return e


def embed_owner():
    e = discord.Embed(title="👑 Owner Commands", description="Reserved for Polarix1954", color=0xDE002A)
    e.add_field(name="/reloadconfig", value="Reload config.json without restart.", inline=False)
    e.add_field(name="/exportdb", value="Export a database backup.", inline=False)
    return e


# ---------- COG ----------
class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # /help
    @app_commands.command(name="help", description="Show help for Demon Translator.")
    async def help_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=embed_general(),
            view=HelpView(interaction.user),
            ephemeral=True
        )

    # /test
    @app_commands.command(name="test", description="Check if the bot is responsive.")
    async def test_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Demon Bot is online and lurking 😈", ephemeral=True)

    # /ping
    @app_commands.command(name="ping", description="Check bot ping.")
    async def ping_cmd(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"🏓 Pong! `{latency}ms`", ephemeral=True)

    # /setmylang — polished
    #
    # Usage 1: /setmylang de        -> saves immediately
    # Usage 2: /setmylang (no args) -> opens a dropdown with flags + names
    #
    @app_commands.command(name="setmylang", description="Set your personal translation language.")
    @app_commands.describe(lang="Language code (e.g., en, de). Leave empty to pick from a dropdown.")
    async def setmylang(self, interaction: discord.Interaction, lang: str | None = None):
        # If a valid code was provided, save directly
        if lang:
            code = lang.lower()
            if code not in SUPPORTED_LANGS:
                return await interaction.response.send_message(
                    f"❌ Unsupported: `{code}`. Try `/langlist` or run `/setmylang` with no value to pick from a list.",
                    ephemeral=True
                )
            await database.set_user_lang(interaction.user.id, code)
            flag, name = LANG_META.get(code, ("🌐", code.upper()))
            return await interaction.response.send_message(
                f"✅ Saved your language as **{flag} {name} ({code})**",
                ephemeral=True
            )

        # No code provided -> open interactive dropdown (ephemeral)
        PER_PAGE = 25
        codes_sorted = sorted(SUPPORTED_LANGS, key=lambda c: LANG_META.get(c, ("🌐", c.upper()))[1])
        pages = [codes_sorted[i:i+PER_PAGE] for i in range(0, len(codes_sorted), PER_PAGE)]
        total_pages = len(pages)

        class PickerView(discord.ui.View):
            def __init__(self, user: discord.User, page_idx: int = 0):
                super().__init__(timeout=60)
                self.user = user
                self.page_idx = page_idx
                self.rebuild()

            def rebuild(self):
                self.clear_items()
                current = pages[self.page_idx]

                options = [
                    discord.SelectOption(
                        label=lang_label(code)[:100],
                        value=code,
                        description=f"Code: {code}"
                    )
                    for code in current
                ]

                select = discord.ui.Select(
                    placeholder=f"Choose your language — Page {self.page_idx+1}/{total_pages}",
                    min_values=1,
                    max_values=1,
                    options=options
                )

                async def on_select(itx: discord.Interaction):
                    if itx.user.id != self.user.id:
                        return await itx.response.defer()
                    code = select.values[0]
                    await database.set_user_lang(self.user.id, code)
                    flag, name = LANG_META.get(code, ("🌐", code.upper()))
                    await itx.response.edit_message(
                        content=f"✅ Saved your language as **{flag} {name} ({code})**",
                        view=None
                    )
                    self.stop()

                select.callback = on_select
                self.add_item(select)

                if total_pages > 1:
                    @discord.ui.button(label="⬅ Previous", style=discord.ButtonStyle.secondary, disabled=self.page_idx == 0)
                    async def prev_btn(itx: discord.Interaction, button: discord.ui.Button):
                        if itx.user.id != self.user.id:
                            return await itx.response.defer()
                        self.page_idx -= 1
                        self.rebuild()
                        await itx.response.edit_message(content=self.content_text(), view=self)

                    @discord.ui.button(label="Next ➡", style=discord.ButtonStyle.primary, disabled=self.page_idx >= total_pages - 1)
                    async def next_btn(itx: discord.Interaction, button: discord.ui.Button):
                        if itx.user.id != self.user.id:
                            return await itx.response.defer()
                        self.page_idx += 1
                        self.rebuild()
                        await itx.response.edit_message(content=self.content_text(), view=self)

            def content_text(self):
                return "Pick your personal translation language 👇"

        view = PickerView(interaction.user)
        await interaction.response.send_message(content=view.content_text(), view=view, ephemeral=True)

    # Optional: autocomplete for typed usage (shows pretty labels but returns code)
    @setmylang.autocomplete("lang")
    async def _auto_lang(self, interaction: discord.Interaction, current: str):
        cur = (current or "").lower()
        matches = [c for c in SUPPORTED_LANGS if cur in c or cur in LANG_META.get(c, ("", ""))[1].lower()]
        return [
            app_commands.Choice(name=lang_label(c)[:100], value=c) for c in matches[:25]
        ]

    # /translate (kept here for discoverability in help; core logic lives in Translate cog)
    @app_commands.command(name="translate", description="Translate a specific text manually.")
    async def translate_stub(self, interaction: discord.Interaction, text: str, lang: str):
        # This stub is here so /help shows a consistent interface;
        # the real /translate is implemented in cogs.translate as well.
        await interaction.response.send_message(
            "Heads up: Use the main **/translate** (this server has it enabled).",
            ephemeral=True
        )

    # /mystats
    @app_commands.command(name="mystats", description="Your translation count.")
    async def mystats(self, interaction: discord.Interaction):
        uid = interaction.user.id
        count = await database.get_user_count(uid)
        await interaction.response.send_message(f"📊 You translated `{count}` messages.", ephemeral=True)

    # /leaderboard
    @app_commands.command(name="leaderboard", description="Top translators globally")
    async def leaderboard(self, interaction: discord.Interaction):
        data = await database.get_top_users(10)
        if not data:
            return await interaction.response.send_message("📭 No stats yet.", ephemeral=True)
        desc = "\n".join([f"**<@{uid}>** — `{count}`" for uid, count in data])
        embed = discord.Embed(title="🌍 Global Leaderboard", description=desc, color=0xDE002A)
        await interaction.response.send_message(embed=embed)

    # /guildstats
    @app_commands.guild_only()
    @app_commands.command(name="guildstats", description="Server translation stats")
    async def guildstats(self, interaction: discord.Interaction):
        gid = interaction.guild.id
        count = await database.get_guild_count(gid)
        await interaction.response.send_message(f"📈 This server translated `{count}` messages.")


async def setup(bot):
    await bot.add_cog(UserCommands(bot))