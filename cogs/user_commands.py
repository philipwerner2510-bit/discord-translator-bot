# cogs/user_commands.py
import discord
from discord.ext import commands
from discord import app_commands

from utils.brand import COLOR, NAME, footer_text  # footer_text is a STRING now
from utils import database
from utils.language_data import SUPPORTED_LANGUAGES, label


class HelpTabs(discord.ui.View):
    def __init__(self, is_admin: bool, is_owner: bool):
        super().__init__(timeout=120)
        # default state
        self.is_admin = is_admin
        self.is_owner = is_owner
        # add buttons
        self.add_item(self.GeneralBtn())
        self.add_item(self.AdminBtn(disabled=not is_admin))
        self.add_item(self.OwnerBtn(disabled=not is_owner))

    class GeneralBtn(discord.ui.Button):
        def __init__(self):
            super().__init__(label="General", style=discord.ButtonStyle.primary, emoji="📖")

        async def callback(self, interaction: discord.Interaction):
            e = discord.Embed(
                title=f"{interaction.client.user.name} — Help (General)",
                color=COLOR,
                description=(
                    "**Slash Commands**\n"
                    "• `/help` — Show this help\n"
                    "• `/guide` — Quick start\n"
                    "• `/setmylang <code>` — Set your personal language\n"
                    "• `/translate <text> <target_lang>` — Translate text with AI\n"
                    "• `/profile` — Show your XP & level\n"
                )
            ).set_footer(text=footer_text)
            await interaction.response.edit_message(embed=e, view=self.view)

    class AdminBtn(discord.ui.Button):
        def __init__(self, disabled: bool = False):
            super().__init__(label="Admin", style=discord.ButtonStyle.secondary, emoji="⚙️", disabled=disabled)

        async def callback(self, interaction: discord.Interaction):
            e = discord.Embed(
                title=f"{interaction.client.user.name} — Help (Admin)",
                color=COLOR,
                description=(
                    "**Admin Commands**\n"
                    "• `/settings` — Show server settings\n"
                    "• `/roles setup` — Create level roles (1–100 in steps)\n"
                    "• `/roles show` — Show configured level roles\n"
                    "• `/roles delete` — Delete all level roles\n"
                    "• `/setemote <emoji>` — Set reaction emoji for auto-translate\n"
                )
            ).set_footer(text=footer_text)
            await interaction.response.edit_message(embed=e, view=self.view)

    class OwnerBtn(discord.ui.Button):
        def __init__(self, disabled: bool = False):
            super().__init__(label="Owner", style=discord.ButtonStyle.danger, emoji="🛠️", disabled=disabled)

        async def callback(self, interaction: discord.Interaction):
            e = discord.Embed(
                title=f"{interaction.client.user.name} — Help (Owner)",
                color=COLOR,
                description=(
                    "**Owner Commands**\n"
                    "• `/owner guilds` — List guilds & members\n"
                    "• `/owner ownerstats` — High-level stats\n"
                )
            ).set_footer(text=footer_text)
            await interaction.response.edit_message(embed=e, view=self.view)


class UserCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show help for Zephyra.")
    async def help(self, interaction: discord.Interaction):
        is_admin = interaction.user.guild_permissions.manage_guild if interaction.guild else False
        is_owner = (interaction.user.id in getattr(self.bot, "owner_ids", set())) or (interaction.user.id == getattr(self.bot, "owner_id", None))

        e = discord.Embed(
            title=f"{NAME} — Help",
            color=COLOR,
            description="Use the tabs below to switch between General, Admin, and Owner help."
        ).set_footer(text=footer_text)

        await interaction.response.send_message(embed=e, view=HelpTabs(is_admin, is_owner), ephemeral=True)

    @app_commands.command(name="guide", description="Quick start guide.")
    async def guide(self, interaction: discord.Interaction):
        e = discord.Embed(
            title="Getting Started",
            color=COLOR,
            description=(
                "1) Set your language: `/setmylang en`\n"
                "2) Admins: choose channels to auto-translate or keep all\n"
                "3) React to messages with the configured emoji to get a DM translation\n"
            )
        ).set_footer(text=footer_text)
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="setmylang", description="Set your personal language preference (ISO code).")
    @app_commands.describe(code="e.g., en, de, es, fr...")
    async def setmylang(self, interaction: discord.Interaction, code: str):
        code = code.lower().strip()
        if not any(l["code"] == code for l in SUPPORTED_LANGUAGES):
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"Unsupported language code `{code}`.",
                    color=COLOR
                ).set_footer(text=footer_text),
                ephemeral=True
            )
        await database.set_user_lang(interaction.user.id, code)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"Your language is now **{label(code)}**.",
                color=COLOR
            ).set_footer(text=footer_text),
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(UserCommands(bot))
