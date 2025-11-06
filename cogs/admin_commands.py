# cogs/admin_commands.py
import discord
from discord.ext import commands
from discord import app_commands

from utils.brand import COLOR, footer_text, NAME
from utils import database
from utils.language_data import SUPPORTED_LANGUAGES, label
from utils.roles import role_ladder
from typing import List

# -------- helpers --------

def _lang_codes() -> List[str]:
    return [l["code"] for l in SUPPORTED_LANGUAGES]

async def ac_lang(interaction: discord.Interaction, current: str):
    """Autocomplete for language code/name/label."""
    cur = (current or "").lower()
    out = []
    for l in SUPPORTED_LANGUAGES:
        code = l["code"]
        disp = label(code)
        name = l["name"].lower()
        if cur in code or cur in name or cur in disp.lower():
            out.append(app_commands.Choice(name=disp, value=code))
        if len(out) >= 25:
            break
    return out

def _fmt_channels(ch_ids: List[int] | None, guild: discord.Guild) -> str:
    if not ch_ids:
        return "All channels (no allow-list set)"
    parts = []
    for cid in ch_ids:
        ch = guild.get_channel(cid)
        parts.append(ch.mention if isinstance(ch, discord.abc.GuildChannel) else f"<#{cid}>")
    return ", ".join(parts) if parts else "—"

# -------- Cog --------

class AdminCommands(commands.Cog):
    """Admin utilities and server configuration."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ----- /settings -----
    @app_commands.command(name="settings", description="(Admin) View current Zephyra configuration")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def settings(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        gid = interaction.guild_id

        # fetch config safely
        try:
            server_lang = await database.get_server_lang(gid)
        except Exception:
            server_lang = None

        try:
            allowed = await database.get_translation_channels(gid)
        except Exception:
            allowed = None

        try:
            emote = await database.get_bot_emote(gid)
        except Exception:
            emote = None

        e = discord.Embed(
            title=f"{NAME} • Server Settings",
            color=COLOR,
            description=(
                f"**Default language:** {label(server_lang) if server_lang else '—'}\n"
                f"**Translation channels:** {_fmt_channels(allowed, interaction.guild)}\n"
                f"**Translate reaction:** {emote or '🔃'}"
            ),
        )
        e.set_footer(text=footer_text)
        await interaction.followup.send(embed=e, ephemeral=True)

    # ----- /defaultlang -----
    @app_commands.command(name="defaultlang", description="(Admin) Set the server's default translation target language")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    @app_commands.describe(code="Target language (code). Try typing: en, de, fr …")
    @app_commands.autocomplete(code=ac_lang)
    async def defaultlang(self, interaction: discord.Interaction, code: str):
        await interaction.response.defer(ephemeral=True)
        code = (code or "").lower()
        if code not in _lang_codes():
            return await interaction.followup.send(
                f"Unsupported language code `{code}`.", ephemeral=True
            )

        try:
            await database.set_server_lang(interaction.guild_id, code)
        except Exception as e:
            return await interaction.followup.send(
                f"Failed to save: `{e}`", ephemeral=True
            )

        e = discord.Embed(
            color=COLOR,
            description=f"✅ Server default language set to **{label(code)}**.",
        )
        e.set_footer(text=footer_text)
        await interaction.followup.send(embed=e, ephemeral=True)

    # ----- /allowchannel -----
    @app_commands.command(name="allowchannel", description="(Admin) Allow a channel for reaction-translate")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def allowchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        try:
            await database.allow_translation_channel(interaction.guild_id, channel.id)
        except Exception as e:
            return await interaction.followup.send(f"Failed: `{e}`", ephemeral=True)

        e = discord.Embed(
            color=COLOR,
            description=f"✅ {channel.mention} added to the translation allow-list."
        )
        e.set_footer(text=footer_text)
        await interaction.followup.send(embed=e, ephemeral=True)

    # ----- /removechannel -----
    @app_commands.command(name="removechannel", description="(Admin) Remove a channel from the translation allow-list")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def removechannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        try:
            await database.remove_translation_channel(interaction.guild_id, channel.id)
        except Exception as e:
            return await interaction.followup.send(f"Failed: `{e}`", ephemeral=True)

        e = discord.Embed(
            color=COLOR,
            description=f"✅ {channel.mention} removed from the translation allow-list."
        )
        e.set_footer(text=footer_text)
        await interaction.followup.send(embed=e, ephemeral=True)

    # ----- /setemote -----
    @app_commands.command(name="setemote", description="(Admin) Set the reaction emoji Zephyra adds for translation")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    @app_commands.describe(emote="Unicode (e.g. 🔃) or custom <:name:id>")
    async def setemote(self, interaction: discord.Interaction, emote: str):
        await interaction.response.defer(ephemeral=True)
        emote = (emote or "").strip()
        if not emote:
            return await interaction.followup.send("Please provide an emoji.", ephemeral=True)

        try:
            await database.set_bot_emote(interaction.guild_id, emote)
        except Exception as e:
            return await interaction.followup.send(f"Failed: `{e}`", ephemeral=True)

        e = discord.Embed(
            color=COLOR,
            description=f"✅ Translate reaction set to {emote}"
        )
        e.set_footer(text=footer_text)
        await interaction.followup.send(embed=e, ephemeral=True)

    # ----- /roles setup -----
    @app_commands.command(name="roles", description="(Admin) Role ladder utilities")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def roles_root(self, interaction: discord.Interaction):
        """Entry point – shows a small helper."""
        await interaction.response.send_message(
            "Use **/roles_setup** to create/sync the level role ladder.",
            ephemeral=True
        )

    @app_commands.command(name="roles_setup", description="(Admin) Create/sync the level role ladder (Lv.1→100)")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def roles_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        welcome_cog = interaction.client.get_cog("Welcome")
        if not welcome_cog or not hasattr(welcome_cog, "ensure_role_ladder"):
            return await interaction.followup.send(
                "Welcome cog not available. Cannot create ladder.", ephemeral=True
            )
        try:
            await welcome_cog.ensure_role_ladder(interaction.guild)
        except Exception as e:
            return await interaction.followup.send(f"Failed: `{e}`", ephemeral=True)

        # preview ladder in embed
        tiers = role_ladder()
        pretty = "\n".join(
            f"• **Lv {t['min_level']:>2}+** — {t['name']}"
            for t in tiers
        )
        e = discord.Embed(
            title="Role Ladder Synced",
            description=pretty,
            color=COLOR
        )
        e.set_footer(text=footer_text)
        await interaction.followup.send(embed=e, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCommands(bot))
