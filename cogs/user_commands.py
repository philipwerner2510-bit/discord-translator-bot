# cogs/user_commands.py
import discord
from discord.ext import commands
from discord import app_commands

from utils.brand import COLOR, NAME
from utils import database
from utils.language_data import SUPPORTED_LANGUAGES, label

def _footer_text():
    try:
        from utils.brand import footer as _f
        return _f() if callable(_f) else str(_f)
    except Exception:
        return f"{NAME} — Developed by Polarix1954"

def _lang_choices(q: str):
    q = (q or "").lower()
    out = []
    for l in SUPPORTED_LANGUAGES:
        disp = f"{l.get('flag','')} {l['code'].upper()} — {l['name']}".strip()
        if not q or q in l["code"].lower() or q in l["name"].lower() or q in disp.lower():
            out.append(app_commands.Choice(name=disp[:100], value=l["code"]))
        if len(out) >= 25:
            break
    return out

async def ac_lang(_, current: str):
    return _lang_choices(current)

class UserCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="guide", description="Quick Zephyra guide")
    async def guide(self, interaction: discord.Interaction):
        e = (
            discord.Embed(
                title="✨ Zephyra Guide",
                description=(
                    "Welcome! Here’s how to get rolling:\n\n"
                    "🌐 **Auto Translate** — react with your server emote to DM a translation.\n"
                    "💬 **/translate** — translate custom text to a target language.\n"
                    "🧩 **/setmylang** — set your personal language for DMs.\n"
                    "📈 **/profile** — see your level, XP bar, and stats.\n"
                    "🏆 **/leaderboard** — top members by XP.\n\n"
                    "⚙️ Admin tools:\n"
                    "• **/defaultlang** set server language\n"
                    "• **/setemote** set the translate reaction emote\n"
                    "• **/seterrorchannel** set/clear error log channel\n"
                    "• **/roles setup/show/delete** level roles ladder\n"
                    "• **/settings** full configuration overview\n"
                ),
                color=COLOR
            )
            .set_footer(text=_footer_text())
        )
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="help", description="Show commands")
    async def help(self, interaction: discord.Interaction):
        user = interaction.user
        guild = interaction.guild

        general = (
            "💬 **/translate**\n"
            "🌐 **/setmylang**\n"
            "📈 **/profile**\n"
            "🏆 **/leaderboard**\n"
            "📜 **/guide**\n"
            "🔗 **/invite**\n"
        )

        is_admin = False
        if guild and isinstance(user, discord.Member):
            is_admin = user.guild_permissions.manage_guild

        admin = (
            "🛠 **/defaultlang**\n"
            "🙂 **/setemote**\n"
            "🚨 **/seterrorchannel**\n"
            "🧱 **/roles setup | /roles show | /roles delete**\n"
            "⚙️ **/settings**\n"
            "📋 **/langlist**\n"
        )

        # owner check (env OWNER_IDS or app owner)
        is_owner = False
        owner_ids_env = []
        try:
            import os
            owner_ids_env = [int(x) for x in os.getenv("OWNER_IDS","").replace(" ","").split(",") if x]
        except Exception:
            owner_ids_env = []
        if user.id in owner_ids_env:
            is_owner = True
        else:
            try:
                appinfo = await self.bot.application_info()
                if user.id == appinfo.owner.id:
                    is_owner = True
            except Exception:
                pass

        owner = "🏁 **/owner** — dashboard (Ping/Stats/Guilds/Reload buttons)\n"

        desc = "### Commands\n" + general
        if is_admin:
            desc += "\n### Admin\n" + admin
        if is_owner:
            desc += "\n### Owner\n" + owner

        e = discord.Embed(title="❓ Help", description=desc, color=COLOR).set_footer(text=_footer_text())
        await interaction.response.send_message(embed=e, ephemeral=True)

    # Personal language with autocomplete
    @app_commands.autocomplete(code=ac_lang)
    @app_commands.describe(code="Your language (code)")
    @app_commands.command(name="setmylang", description="Set your personal language for DM translations.")
    async def setmylang(self, interaction: discord.Interaction, code: str):
        code = (code or "").lower()
        valid = {l["code"] for l in SUPPORTED_LANGUAGES}
        if code not in valid:
            return await interaction.response.send_message("❌ Unknown language code.", ephemeral=True)
        await database.set_user_lang(interaction.user.id, code)
        await interaction.response.send_message(f"✅ Personal language set to **{label(code)}**.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(UserCommands(bot))
