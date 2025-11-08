# cogs/user_commands.py
import discord
from discord.ext import commands
from discord import app_commands

from utils.language_data import SUPPORTED_LANGUAGES, label
from utils import database

# Brand + Zephyra emoji fallbacks
try:
    from utils.brand import COLOR
except Exception:
    COLOR = 0x00E6F6
try:
    from utils.brand import FOOTER as BRAND_FOOTER
except Exception:
    BRAND_FOOTER = "Zephyra • /help for commands"

# Optional Zephyra emotes (fallback to unicode if not present)
def _z(name: str, default: str) -> str:
    try:
        from utils import brand as _b
        return getattr(_b, name, default)
    except Exception:
        return default

EMO_USER  = _z("Z_SPARKLES", "✨")
EMO_ADMIN = _z("Z_WRENCH",   "🛠️")
EMO_OWNER = _z("Z_CROWN",    "👑")

def is_admin(member: discord.Member | None) -> bool:
    return bool(member and member.guild_permissions.manage_guild)

def is_owner(user: discord.User, app_info) -> bool:
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

        # Tabs (Support link removed)
        self.add_item(self._btn("User",  EMO_USER,  "user"))
        if self.show_admin:
            self.add_item(self._btn("Admin", EMO_ADMIN, "admin"))
        if self.show_owner:
            self.add_item(self._btn("Owner", EMO_OWNER, "owner"))

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

    # Show key options/values inline for clarity
    user_block = (
        f"**{EMO_USER} User**\n"
        "• `/guide` — Quick start\n"
        "• `/translate text:<text> target_lang:<code>` — Translate\n"
        "• `/profile [user]` — XP profile with progress bar\n"
        "• `/leaderboard` — XP top users\n"
        "• `/setmylang code:<code>` — Personal language (auto-complete)\n"
        "• `/invite` — Bot invite link\n"
    )

    admin_block = (
        f"**{EMO_ADMIN} Admin**\n"
        "• `/defaultlang code:<code>` — Set server default language\n"
        "• `/settings` — Emote, error channel & allowed channels\n"
        "• `/setemote emote:<emoji|<:name:id>>` — Reaction emoji\n"
        "• `/seterrorchannel [channel]` — Set or clear error channel\n"
        "• `/roles setup` — Create level roles (1–100 in steps of 10)\n"
        "• `/roles show` — Show the ladder\n"
        "• `/roles delete` — Remove the ladder\n"
        "• `/langlist` — List 50 common languages (paged)\n"
    )

    owner_block = (
        f"**{EMO_OWNER} Owner**\n"
        "• `/owner` — Dashboard with buttons: Ping, Stats, Guilds\n"
        "  (standalone `/stats` removed, `/reload` removed)\n"
    )

    if section == "admin":
        desc = user_block + "\n" + admin_block
    elif section == "owner":
        desc = user_block
        if show_admin:
            desc += "\n" + admin_block
        desc += "\n" + owner_block
    else:  # "user"
        desc = user_block
        if show_admin:
            desc += "\n" + admin_block
        if show_owner:
            desc += "\n" + owner_block

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
                "✨ **Translate:** React with your emote or use `/translate`.\n"
                "🌐 **Languages:** `/defaultlang` (server), `/setmylang` (you).\n"
                "💬 **Channels:** Limit auto-translate per channel.\n"
                "📈 **XP:** Messages, translations, voice → level roles.\n"
                "🏆 **Profiles:** `/profile` with a clean tilted bar.\n"
                "⚙️ **Settings:** `/settings` shows emote, error channel & channels."
            ),
            color=COLOR
        )
        e.set_footer(text=BRAND_FOOTER)
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="help", description="Show help with tabs.")
    async def help(self, interaction: discord.Interaction):
        member = interaction.user if isinstance(interaction.user, discord.Member) else (
            interaction.guild.get_member(interaction.user.id) if interaction.guild else None
        )
        show_admin = is_admin(member) if isinstance(member, discord.Member) else False
        app_info = await self.bot.application_info()
        show_owner = is_owner(interaction.user, app_info)

        embed = build_help_embed("user", show_admin, show_owner)
        view = HelpView(show_admin, show_owner)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(UserCommands(bot))
