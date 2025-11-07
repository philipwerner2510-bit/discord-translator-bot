# cogs/user_commands.py
import discord
from discord.ext import commands
from discord import app_commands

from utils.brand import COLOR, footer_text as _footer_text, Z_HAPPY, Z_EXCITED
from utils import database
from utils.language_data import SUPPORTED_LANGUAGES, label

def FOOT(): return _footer_text() if callable(_footer_text) else _footer_text

# --------- autocomplete for /setmylang ----------
async def ac_lang(interaction: discord.Interaction, current: str):
    current = (current or "").lower()
    out = []
    for l in SUPPORTED_LANGUAGES:
        disp = f"{label(l['code'])} ({l['code']})"
        if current in l["code"] or current in l["name"].lower() or current in disp.lower():
            out.append(app_commands.Choice(name=f"{disp}", value=l["code"]))
        if len(out) >= 25: break
    return out

class User(commands.Cog):
    def __init__(self, bot): self.bot = bot

    # --------- /guide (Zephyra themed) ----------
    @app_commands.command(name="guide", description="Quick guide for using Zephyra.")
    async def guide(self, interaction: discord.Interaction):
        desc = (
            f"{Z_EXCITED} **How to use Zephyra**\n"
            "• Add the translate reaction in allowed channels to get a DM translation.\n"
            "• Use `/setmylang` to choose your target language.\n"
            "• Admins: use `/defaultlang`, `/settings`, `/roles setup`.\n"
            "• Need help? `/help` shows all commands.\n\n"
            f"{Z_HAPPY} **Tips**\n"
            "• You can upload `.txt` or `.md` attachments — Zephyra translates them too.\n"
            "• XP: messages, voice time and translations give progress. Check `/profile`.\n"
        )
        e = discord.Embed(title="Zephyra — Quick Guide", description=desc, color=COLOR)
        e.set_footer(text=FOOT())
        await interaction.response.send_message(embed=e, ephemeral=True)

    # --------- /help ----------
    @app_commands.command(name="help", description="See commands.")
    async def help(self, interaction: discord.Interaction):
        is_admin = interaction.user.guild_permissions.manage_guild
        is_owner = interaction.user.id in {1425590836800000170, 297620229339250689}

        general = (
            "`/guide`, `/help`, `/invite`, `/translate`, `/setmylang`, `/profile`, `/leaderboard`"
        )
        admin = (
            "`/defaultlang`, `/langlist`, `/seterrorchannel`, `/settings`, "
            "`/roles setup`, `/roles show`, `/roles delete`, `/setemote`"
        )
        owner = "`/owner` (buttons for Stats, Guilds, Self-test, Reload)"

        e = discord.Embed(title="Zephyra — Help", color=COLOR)
        e.add_field(name="General", value=general, inline=False)
        if is_admin or is_owner:
            e.add_field(name="Admin", value=admin, inline=False)
        if is_owner:
            e.add_field(name="Owner", value=owner, inline=False)
        e.set_footer(text=FOOT())
        await interaction.response.send_message(embed=e, ephemeral=True)

    # --------- /setmylang ----------
    @app_commands.command(name="setmylang", description="Set your preferred translation target language.")
    @app_commands.autocomplete(code=ac_lang)
    @app_commands.describe(code="Language code (autocomplete: name, code or flag label)")
    async def setmylang(self, interaction: discord.Interaction, code: str):
        code = code.lower().strip()
        if code not in [l["code"] for l in SUPPORTED_LANGUAGES]:
            return await interaction.response.send_message(
                embed=discord.Embed(description=f"Unsupported language `{code}`.", color=COLOR).set_footer(text=FOOT()),
                ephemeral=True
            )
        await database.set_user_lang(interaction.user.id, code)
        await interaction.response.send_message(
            embed=discord.Embed(description=f"Your language set to **{label(code)}**.", color=COLOR).set_footer(text=FOOT()),
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(User(bot))
