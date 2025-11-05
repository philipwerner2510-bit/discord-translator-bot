# cogs/user_commands.py
import os
import discord
from discord.ext import commands
from discord import app_commands

OWNER_ID = int(os.getenv("OWNER_ID", "762267166031609858"))
BRAND_COLOR = 0x00E6F6  # Zephyra cyan

def is_owner(user: discord.abc.User) -> bool:
    return user.id == OWNER_ID

def embed_general() -> discord.Embed:
    e = discord.Embed(
        title="Zephyra — Help (General)",
        color=BRAND_COLOR,
        description=(
            "Commands available to everyone.\n"
            "_Tip: Use Tab/Autocomplete on language fields._"
        )
    )
    e.add_field(
        name="`/translate <text> <target_lang>`",
        value=(
            "Translate **text** to a chosen **language code** (e.g. `en`, `de`, `fr`).\n"
            "• Uses **AI translation only** (no Libre fallback).\n"
            "• Returns a clean translated message."
        ),
        inline=False,
    )
    e.add_field(
        name="`/setmylang <lang>`",
        value=(
            "Set your **personal default language** for DM translations triggered by reaction.\n"
            "• Supports **autocomplete** for codes."
        ),
        inline=False,
    )
    e.add_field(
        name="`/ping`",
        value="Quick latency check.",
        inline=False,
    )
    e.add_field(
        name="`/guide`",
        value="Show the quick-start guide for all users.",
        inline=False,
    )
    # optional, if you have /invite live in your build
    e.add_field(
        name="`/invite`",
        value="DMs you an invite link to add Zephyra to another server.",
        inline=False,
    )
    e.set_footer(text="Created by @Polarix1954")
    return e

def embed_admin() -> discord.Embed:
    e = discord.Embed(
        title="Zephyra — Help (Admin)",
        color=BRAND_COLOR,
        description="Admin-only configuration commands."
    )
    e.add_field(
        name="`/defaultlang <lang>`",
        value=(
            "Set the **server default language** (fallback for users who didn’t set a personal one).\n"
            "• Supports **autocomplete** for codes."
        ),
        inline=False,
    )
    e.add_field(
        name="`/channelselection`",
        value=(
            "Select **which channels** Zephyra should watch and react in.\n"
            "• The bot adds a reaction to messages in these channels. "
            "Users can click it to receive a DM translation."
        ),
        inline=False,
    )
    e.add_field(
        name="`/emote <emoji>`",
        value=(
            "Set the **reaction emote** Zephyra uses in watched channels.\n"
            "• Accepts **Unicode** (e.g. `👍`) **or** a **custom emoji from THIS server** (e.g. `<:name:id>`).\n"
            "• Validates that custom emoji actually belongs to the current server."
        ),
        inline=False,
    )
    e.add_field(
        name="`/seterrorchannel <#channel | none>`",
        value=(
            "Set an **error log channel**, or pass `none` to clear."
        ),
        inline=False,
    )
    e.add_field(
        name="`/settings`",
        value="Show current server settings (default lang, emote, error channel, watched channels).",
        inline=False,
    )
    e.set_footer(text="Created by @Polarix1954")
    return e

def embed_owner() -> discord.Embed:
    e = discord.Embed(
        title="Zephyra — Help (Owner)",
        color=BRAND_COLOR,
        description="Owner-only controls."
    )
    e.add_field(
        name="`/stats`",
        value=(
            "Show **bot stats**: servers, uptime, **monthly AI tokens** (in/out) & **estimated EUR**, "
            "and translation totals (today / lifetime)."
        ),
        inline=False,
    )
    e.set_footer(text="Created by @Polarix1954 • Owner only")
    return e

class HelpView(discord.ui.View):
    def __init__(self, show_admin: bool, show_owner: bool):
        super().__init__(timeout=120)
        self.show_admin = show_admin
        self.show_owner = show_owner

        # Always add General
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

    # /help
    @app_commands.command(name="help", description="Show Zephyra help.")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user = interaction.user
        is_admin = interaction.guild and user.guild_permissions.administrator
        show_owner = is_owner(user)
        v = HelpView(show_admin=bool(is_admin or show_owner), show_owner=show_owner)
        await interaction.followup.send(embed=embed_general(), view=v, ephemeral=True)

    # /ping (everyone)
    @app_commands.command(name="ping", description="Check bot latency.")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        latency_ms = round(self.bot.latency * 1000)
        await interaction.followup.send(f"🏓 Pong! `{latency_ms} ms`", ephemeral=True)

    # NOTE: /guide exists in another cog (welcome/guide). We keep /help clean here.

async def setup(bot):
    await bot.add_cog(UserCommands(bot))