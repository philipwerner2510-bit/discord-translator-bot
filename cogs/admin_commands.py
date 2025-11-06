# cogs/admin_commands.py
import discord
from discord.ext import commands
from discord import app_commands

from utils.brand import COLOR, NAME, footer_text as BRAND_FOOTER
from utils import database
from utils.roles import role_ladder
from utils.language_data import SUPPORTED_LANGUAGES, label

def _footer_text() -> str:
    try:
        return BRAND_FOOTER() if callable(BRAND_FOOTER) else str(BRAND_FOOTER)
    except Exception:
        return "Zephyra • Developed by Polarix1954"

# ---- language autocomplete
async def ac_lang(interaction: discord.Interaction, current: str):
    cur = (current or "").lower()
    choices = []
    for l in SUPPORTED_LANGUAGES:
        disp = label(l["code"])
        if cur in l["code"] or cur in l["name"].lower() or cur in disp.lower():
            choices.append(app_commands.Choice(name=disp, value=l["code"]))
        if len(choices) >= 25:
            break
    return choices

class AdminCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- /defaultlang (server)
    @app_commands.command(name="defaultlang", description="Set the default translation language for this server.")
    @app_commands.describe(code="Target language code (e.g., en, de, fr...)")
    @app_commands.autocomplete(code=ac_lang)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def defaultlang(self, interaction: discord.Interaction, code: str):
        code = (code or "").lower()
        valid = {l["code"] for l in SUPPORTED_LANGUAGES}
        if code not in valid:
            return await interaction.response.send_message(
                f"Unsupported language code `{code}`.", ephemeral=True
            )
        await database.set_server_lang(interaction.guild.id, code)
        e = discord.Embed(
            title=f"{NAME} • Server Language",
            description=f"Default language set to **{label(code)}**.",
            color=COLOR
        )
        e.set_footer(text=_footer_text())
        await interaction.response.send_message(embed=e, ephemeral=True)

    # --- /setchannels add/remove/list (translation reaction allow-list)
    channels = app_commands.Group(name="setchannels", description="Configure which channels get the translate reaction")

    @channels.command(name="add", description="Allow translate reaction in this channel")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def channels_add(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await database.allow_translation_channel(interaction.guild.id, channel.id)
        e = discord.Embed(description=f"✅ Allowed translations in {channel.mention}", color=COLOR)
        e.set_footer(text=_footer_text())
        await interaction.response.send_message(embed=e, ephemeral=True)

    @channels.command(name="remove", description="Remove channel from allow-list")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def channels_remove(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await database.remove_translation_channel(interaction.guild.id, channel.id)
        e = discord.Embed(description=f"➖ Removed {channel.mention} from allow-list", color=COLOR)
        e.set_footer(text=_footer_text())
        await interaction.response.send_message(embed=e, ephemeral=True)

    @channels.command(name="list", description="Show current allow-list")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def channels_list(self, interaction: discord.Interaction):
        allowed = await database.get_translation_channels(interaction.guild.id)
        if not allowed:
            txt = "No allow-list set — **all channels** are eligible."
        else:
            mentions = []
            for cid in allowed:
                ch = interaction.guild.get_channel(cid)
                mentions.append(ch.mention if ch else f"`#{cid}`")
            txt = "Allowed channels:\n" + ", ".join(mentions)
        e = discord.Embed(description=txt, color=COLOR)
        e.set_footer(text=_footer_text())
        await interaction.response.send_message(embed=e, ephemeral=True)

    # --- /roles setup (create level ladder roles 1-100 in 10 steps)
    @app_commands.command(name="roles", description="Create the level role ladder (10 roles).")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def roles_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        created, skipped = [], []
        existing = {r.name for r in interaction.guild.roles}
        for spec in role_ladder():
            if spec["name"] in existing:
                skipped.append(spec["name"])
                continue
            try:
                await interaction.guild.create_role(
                    name=spec["name"],
                    colour=discord.Colour(spec["color"]),
                    reason="Initialize Zephyra level role ladder (levels 1–100)"
                )
                created.append(spec["name"])
            except Exception:
                skipped.append(spec["name"])
        msg = []
        if created: msg.append(f"✅ Created: {', '.join(created)}")
        if skipped: msg.append(f"⏭️ Skipped: {', '.join(skipped)}")
        e = discord.Embed(
            title=f"{NAME} • Level Roles",
            description="\n".join(msg) or "Nothing to do.",
            color=COLOR
        )
        e.set_footer(text=_footer_text())
        await interaction.followup.send(embed=e, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCommands(bot))
