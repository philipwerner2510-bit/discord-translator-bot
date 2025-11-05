import os
import discord
from discord.ext import commands
from discord import app_commands
from utils import database
from utils.brand import COLOR, EMOJI_PRIMARY, EMOJI_HIGHLIGHT, EMOJI_ACCENT, footer

OWNER_ID = int(os.getenv("OWNER_ID", "762267166031609858"))

SUPPORTED_LANGS = [
    "en","zh","hi","es","fr","ar","bn","pt","ru","ja",
    "de","jv","ko","vi","mr","ta","ur","tr","it","th",
    "gu","kn","ml","pa","or","fa","sw","am","ha","yo"
]

async def ac_lang(interaction: discord.Interaction, current: str):
    current = (current or "").lower()
    items = [code for code in SUPPORTED_LANGS if current in code]
    return [app_commands.Choice(name=code, value=code) for code in items[:25]]

def embed_general() -> discord.Embed:
    e = discord.Embed(
        title=f"{EMOJI_PRIMARY} Zephyra — Help (General)",
        color=COLOR,
        description="Commands available to everyone.\n_Tip: language fields support autocomplete._"
    )
    e.add_field(
        name="`/translate <text> <target_lang>`",
        value="Translate text to a chosen language code (e.g., `en`, `de`, `fr`).",
        inline=False,
    )
    e.add_field(
        name="`/setmylang <lang>`",
        value="Set your personal default language for DM translations (autocomplete).",
        inline=False,
    )
    e.add_field(name="`/ping`", value="Latency check.", inline=False)
    e.add_field(name="`/guide`", value="Quick-start guide (admin posts it publicly).", inline=False)
    e.add_field(name="`/invite`", value="DMs you the invite link to add Zephyra.", inline=False)
    e.set_footer(text=footer())
    return e

def embed_admin() -> discord.Embed:
    e = discord.Embed(
        title=f"{EMOJI_HIGHLIGHT} Zephyra — Help (Admin)",
        color=COLOR,
        description="Admin-only configuration commands."
    )
    e.add_field(name="`/defaultlang <lang>`", value="Set server default language (autocomplete).", inline=False)
    e.add_field(name="`/channelselection`", value="Choose channels Zephyra should watch/react in.", inline=False)
    e.add_field(
        name="`/emote <emoji>`",
        value="Set reaction emote (Unicode or this server’s custom emoji `<:name:id>`).",
        inline=False,
    )
    e.add_field(name="`/seterrorchannel <#channel | none>`", value="Set/clear error log channel.", inline=False)
    e.add_field(name="`/settings`", value="Show server settings.", inline=False)
    e.set_footer(text=footer())
    return e

def embed_owner() -> discord.Embed:
    e = discord.Embed(
        title=f"{EMOJI_ACCENT} Zephyra — Help (Owner)",
        color=COLOR,
        description="Owner-only utilities."
    )
    e.add_field(
        name="`/stats`",
        value="Servers, uptime, **monthly AI tokens** (in/out), estimated EUR, and translation totals.",
        inline=False,
    )
    e.set_footer(text=footer())
    return e

class HelpView(discord.ui.View):
    def __init__(self, show_admin: bool, show_owner: bool):
        super().__init__(timeout=120)
        self.show_admin = show_admin
        self.show_owner = show_owner
        self.add_item(self.GeneralButton())
        if show_admin:
            self.add_item(self.AdminButton())
        if show_owner:
            self.add_item(self.OwnerButton())

    class GeneralButton(discord.ui.Button):
        def __init__(self):
            super().__init__(label="General", style=discord.ButtonStyle.primary)
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.edit_message(embed=embed_general(), view=self.view)

    class AdminButton(discord.ui.Button):
        def __init__(self):
            super().__init__(label="Admin", style=discord.ButtonStyle.secondary)
        async def callback(self, interaction: discord.Interaction):
            view: HelpView = self.view  # type: ignore
            if not view.show_admin:
                return await interaction.response.send_message("You don't have permission to view Admin help.", ephemeral=True)
            await interaction.response.edit_message(embed=embed_admin(), view=view)

    class OwnerButton(discord.ui.Button):
        def __init__(self):
            super().__init__(label="Owner", style=discord.ButtonStyle.secondary)
        async def callback(self, interaction: discord.Interaction):
            view: HelpView = self.view  # type: ignore
            if not view.show_owner:
                return await interaction.response.send_message("Owner only.", ephemeral=True)
            await interaction.response.edit_message(embed=embed_owner(), view=view)

class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show Zephyra help.")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user = interaction.user
        is_admin = interaction.guild and user.guild_permissions.administrator
        show_owner = (user.id == OWNER_ID)
        v = HelpView(show_admin=bool(is_admin or show_owner), show_owner=show_owner)
        await interaction.followup.send(embed=embed_general(), view=v, ephemeral=True)

    @app_commands.command(name="ping", description="Check bot latency.")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        latency_ms = round(self.bot.latency * 1000)
        e = discord.Embed(description=f"🏓 Pong! `{latency_ms} ms`", color=COLOR)
        e.set_footer(text=footer())
        await interaction.followup.send(embed=e, ephemeral=True)

    @app_commands.command(name="setmylang", description="Set your personal default translation language.")
    @app_commands.describe(lang="Language code (e.g., en, de, fr)")
    @app_commands.autocomplete(lang=ac_lang)
    async def setmylang(self, interaction: discord.Interaction, lang: str):
        await interaction.response.defer(ephemeral=True)
        lang = (lang or "").lower().strip()
        if lang not in SUPPORTED_LANGS:
            e = discord.Embed(description=f"❌ Unsupported language code `{lang}`.", color=COLOR)
            e.set_footer(text=footer())
            return await interaction.followup.send(embed=e, ephemeral=True)
        await database.set_user_lang(interaction.user.id, lang)
        e = discord.Embed(description=f"✅ Your personal language has been set to `{lang}`.", color=COLOR)
        e.set_footer(text=footer())
        await interaction.followup.send(embed=e, ephemeral=True)

async def setup(bot):
    await bot.add_cog(UserCommands(bot))