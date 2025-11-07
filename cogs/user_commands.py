# cogs/user_commands.py
import discord
from discord.ext import commands
from discord import app_commands

from utils.language_data import SUPPORTED_LANGUAGES, label
from utils import database

# brand-safe imports
try:
    from utils.brand import COLOR
except Exception:
    COLOR = 0x00E6F6
try:
    from utils.brand import FOOTER as BRAND_FOOTER
except Exception:
    BRAND_FOOTER = "Zephyra • /help for commands"

def is_admin(member: discord.Member | None) -> bool:
    return bool(member and member.guild_permissions.manage_guild)

def is_owner(user: discord.User, app_info) -> bool:
    # app_info is discord.AppInfo; avoid version-specific typing
    try:
        owner = getattr(app_info, "owner", None)
        return bool(owner and getattr(owner, "id", None) == user.id)
    except Exception:
        return False

class HelpView(discord.ui.View):
    def __init__(self, show_admin: bool, show_owner: bool):
        super().__init__(timeout=120)
        self.show_admin = show_admin
        self.show_owner = show_owner

        # Links
        self.add_item(discord.ui.Button(
            label="Invite",
            style=discord.ButtonStyle.link,
            url="https://discord.com/api/oauth2/authorize?client_id=1425590836800000170&permissions=8&scope=bot%20applications.commands"
        ))
        self.add_item(discord.ui.Button(
            label="Support",
            style=discord.ButtonStyle.link,
            url="https://discord.gg/"
        ))

        # Tabs
        self.add_item(self._btn("General", "✨", "general"))
        if self.show_admin:
            self.add_item(self._btn("Admin", "🛠️", "admin"))
        if self.show_owner:
            self.add_item(self._btn("Owner", "👑", "owner"))

    def _btn(self, label_txt: str, emoji: str, key: str):
        b = discord.ui.Button(label=label_txt, emoji=emoji, style=discord.ButtonStyle.primary)
        async def cb(inter: discord.Interaction):
            embed = build_help_embed(key, self.show_admin, self.show_owner)
            await inter.response.edit_message(embed=embed, view=self)
        b.callback = cb
        return b

def build_help_embed(section: str, show_admin: bool, show_owner: bool) -> discord.Embed:
    e = discord.Embed(title="Zephyra — Help", color=COLOR)
    e.set_footer(text=BRAND_FOOTER)

    general = (
        "**Public**\n"
        "• `/guide` — Quick start & features\n"
        "• `/translate text:<text> target_lang:<code>` — Translate text\n"
        "• `/profile [user]` — Show XP profile\n"
        "• `/leaderboard` — Top XP users\n"
        "• `/setmylang code:<code>` — Personal language (auto-complete)\n"
        "• `/invite` — Bot invite link\n"
    )
    admin = (
        "**Admin**\n"
        "• `/defaultlang code:<code>` — Set server default language\n"
        "• `/settings` — Emote, error channel & allowed channels\n"
        "• `/setemote emote:<emoji or <:name:id>>` — Translate reaction\n"
        "• `/seterrorchannel [channel]` — Set/clear error channel\n"
        "• `/roles setup` — Create level role ladder (1-100)\n"
        "• `/roles show` — Show the ladder\n"
        "• `/roles delete` — Remove the ladder\n"
        "• `/langlist` — List common languages (paged)\n"
    )
    owner = (
        "**Owner**\n"
        "• `/owner` — Dashboard with buttons: Ping, Stats, Guilds, Reload\n"
    )

    if section == "admin":
        desc = "✨ **General**\n" + general + "\n🛠️ **Admin**\n" + admin
    elif section == "owner":
        desc = "✨ **General**\n" + general
        if show_admin:
            desc += "\n🛠️ **Admin**\n" + admin
        desc += "\n👑 **Owner**\n" + owner
    else:
        desc = "✨ **General**\n" + general
        if show_admin:
            desc += "\n🛠️ **Admin**\n" + admin
        if show_owner:
            desc += "\n👑 **Owner**\n" + owner

    e.description = desc
    return e

class UserCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="guide", description="Show a styled quick-start guide.")
    async def guide(self, interaction: discord.Interaction):
        e = discord.Embed(
            title="🌬️ Zephyra — Quick Start",
            description=(
                "✨ **Translate fast:** React with your server emote or use `/translate`.\n"
                "🌐 **Languages:** `/defaultlang` for server, `/setmylang` for you.\n"
                "💬 **Channels:** Limit auto-translate to selected channels.\n"
                "📈 **XP:** Messages, translations, voice → roles.\n"
                "🏆 **Profiles:** `/profile` for a clean tilted progress bar.\n"
                "⚙️ **Settings:** `/settings` shows emote, error channel & channels."
            ),
            color=COLOR
        )
        e.set_footer(text=BRAND_FOOTER)
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="help", description="Show help with buttons.")
    async def help(self, interaction: discord.Interaction):
        member = interaction.user if isinstance(interaction.user, discord.Member) else interaction.guild.get_member(interaction.user.id)
        show_admin = is_admin(member) if isinstance(member, discord.Member) else False
        app_info = await self.bot.application_info()
        show_owner = is_owner(interaction.user, app_info)

        embed = build_help_embed("general", show_admin, show_owner)
        view = HelpView(show_admin, show_owner)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(UserCommands(bot))
