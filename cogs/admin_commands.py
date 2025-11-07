# cogs/admin_commands.py
import discord
from discord.ext import commands
from discord import app_commands

from utils.brand import COLOR, footer_text as _footer_text
from utils.roles import gradient_color
from utils import database
from utils.language_data import SUPPORTED_LANGUAGES, label

def FOOT():
    # brand.footer_text is a string in your build; if it ever turns into a function, this still works.
    return _footer_text() if callable(_footer_text) else _footer_text

OWNER_IDS = {1425590836800000170, 297620229339250689}  # you + (optionally) alt

def is_admin():
    def predicate(interaction: discord.Interaction) -> bool:
        m = interaction.user
        return m.guild_permissions.manage_guild or m.id in OWNER_IDS
    return app_commands.check(predicate)

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    group_roles = app_commands.Group(name="roles", description="Level role tools")

    # ---------- LANGUAGE ----------
    @app_commands.command(name="defaultlang", description="Set server default language code (e.g., en, de).")
    @is_admin()
    @app_commands.describe(code="ISO 639-1 code, e.g., en, de, es")
    async def defaultlang(self, interaction: discord.Interaction, code: str):
        code = code.lower().strip()
        if code not in [l["code"] for l in SUPPORTED_LANGUAGES]:
            return await interaction.response.send_message(
                embed=discord.Embed(description=f"Unsupported language `{code}`.", color=COLOR).set_footer(text=FOOT()),
                ephemeral=True
            )
        await database.set_server_lang(interaction.guild.id, code)
        await interaction.response.send_message(
            embed=discord.Embed(description=f"Server default language set to **{label(code)}**.", color=COLOR).set_footer(text=FOOT()),
            ephemeral=True
        )

    @app_commands.command(name="langlist", description="Show the available languages (admin-only).")
    @is_admin()
    async def langlist(self, interaction: discord.Interaction):
        langs = [f"`{l['code']}` — {label(l['code'])}" for l in SUPPORTED_LANGUAGES[:50]]
        e = discord.Embed(title="Supported Languages (Top 50)", description="\n".join(langs), color=COLOR)
        e.set_footer(text=FOOT())
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="seterrorchannel", description="Set (or clear) the error log channel.")
    @is_admin()
    @app_commands.describe(channel="Channel for error logs. Leave empty to clear.")
    async def seterrorchannel(self, interaction: discord.Interaction, channel: discord.TextChannel | None = None):
        await database.set_error_channel(interaction.guild.id, channel.id if channel else None)
        msg = f"Error channel set to {channel.mention}" if channel else "Error channel cleared."
        await interaction.response.send_message(
            embed=discord.Embed(description=msg, color=COLOR).set_footer(text=FOOT()), ephemeral=True
        )

    # ---------- SETTINGS ----------
    @app_commands.command(name="settings", description="Show server translation settings.")
    @is_admin()
    async def settings(self, interaction: discord.Interaction):
        gid = interaction.guild.id
        server_lang = await database.get_server_lang(gid) or "en"
        emote = await database.get_bot_emote(gid) or "🔃"
        allowed = await database.get_translation_channels(gid)

        if allowed is None:
            channels_str = "All channels (no allow-list set)"
        elif not allowed:
            channels_str = "None (no channels in allow-list)"
        else:
            mentions = []
            for cid in allowed:
                ch = interaction.guild.get_channel(cid)
                mentions.append(ch.mention if ch else f"`#{cid}`")
            channels_str = ", ".join(mentions)

        e = (discord.Embed(title="Server Settings", color=COLOR)
             .add_field(name="Default language", value=f"**{label(server_lang)}** (`{server_lang}`)", inline=True)
             .add_field(name="Bot emote", value=emote, inline=True)
             .add_field(name="Allowed translation channels", value=channels_str, inline=False)
             .set_footer(text=FOOT()))
        await interaction.response.send_message(embed=e, ephemeral=True)

    # ---------- ROLES ----------
    @group_roles.command(name="setup", description="Create level roles (1–100 in 10-level steps).")
    @is_admin()
    async def roles_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        # Names (Discord-themed, not Zephyra)
        names = ["Newbie","Regular","Member+","Active","Veteran",
                 "Elite","Epic","Legendary","Mythic","Ascendant"]
        start_hex = "#7D2EE6"  # purple
        end_hex   = "#00E6F6"  # Zephyra cyan

        mapping = []
        for i in range(10):
            lvl_start = 10*i+1
            lvl_end   = 10*(i+1)
            t = i/9 if i>0 else 0.0
            color_int = gradient_color(start_hex, end_hex, t)
            name = f"{names[i]} (Lv {lvl_start}-{lvl_end})"

            role = discord.utils.get(guild.roles, name=name)
            if role is None:
                role = await guild.create_role(name=name, colour=discord.Colour(color_int), reason="Zephyra level roles")
            else:
                await role.edit(colour=discord.Colour(color_int), reason="Zephyra level roles refresh")

            mapping.append((lvl_start, lvl_end, role.id))

        await database.upsert_role_table(guild.id, mapping)
        await interaction.followup.send(
            embed=discord.Embed(description="✅ Level roles created/updated and saved.", color=COLOR).set_footer(text=FOOT()),
            ephemeral=True
        )

    @group_roles.command(name="show", description="Show current level role mapping.")
    @is_admin()
    async def roles_show(self, interaction: discord.Interaction):
        rows = await database.get_role_table(interaction.guild.id)
        if not rows:
            return await interaction.response.send_message(
                embed=discord.Embed(description="No role table saved yet.", color=COLOR).set_footer(text=FOOT()),
                ephemeral=True
            )
        lines = []
        for ls, le, rid in rows:
            role = interaction.guild.get_role(rid)
            lines.append(f"Lv **{ls}-{le}** → {role.mention if role else f'`@deleted ({rid})`'}")
        e = discord.Embed(title="Level Role Table", description="\n".join(lines), color=COLOR)
        e.set_footer(text=FOOT())
        await interaction.response.send_message(embed=e, ephemeral=True)

    @group_roles.command(name="delete", description="Delete level role mapping (does not delete roles).")
    @is_admin()
    async def roles_delete(self, interaction: discord.Interaction):
        n = await database.delete_role_table(interaction.guild.id)
        await interaction.response.send_message(
            embed=discord.Embed(description=f"🗑️ Deleted mapping entries: **{n}**.", color=COLOR).set_footer(text=FOOT()),
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Admin(bot))
