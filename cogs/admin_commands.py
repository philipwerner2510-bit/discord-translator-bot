# cogs/admin_commands.py
import os
import math
import discord
from discord.ext import commands
from discord import app_commands

from utils.brand import COLOR, NAME
from utils import database
from utils.language_data import SUPPORTED_LANGUAGES, label

# ---------- helpers ----------
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

def _grad(a: int, b: int, t: float) -> int:
    return max(0, min(255, int(round(a + (b - a) * t))))

def _rgb_to_int(r: int, g: int, b: int) -> int:
    return (r << 16) + (g << 8) + b

def _ladder_colors(n: int, start_rgb=(128, 90, 213), end_rgb=(0, 230, 246)):
    # start ~ purple, end ~ Zephyra cyan
    for i in range(n):
        t = i / max(1, n - 1)
        r = _grad(start_rgb[0], end_rgb[0], t)
        g = _grad(start_rgb[1], end_rgb[1], t)
        b = _grad(start_rgb[2], end_rgb[2], t)
        yield _rgb_to_int(r, g, b)

def _make_role_names():
    # Discord-themed, neutral names (no Zephyra in the name)
    return [
        "Newcomer", "Rising", "Active", "Chatter", "Talkative",
        "Conversationalist", "Vocal", "Enthusiast", "Veteran", "Legend"
    ]

# ---------- checks ----------
def is_guild_admin():
    def predicate(interaction: discord.Interaction):
        return interaction.user.guild_permissions.manage_guild if interaction.guild else False
    return app_commands.check(predicate)

# ---------- cog ----------
class AdminCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # /defaultlang
    @is_guild_admin()
    @app_commands.autocomplete(code=ac_lang)
    @app_commands.describe(code="Server default language code")
    @app_commands.command(name="defaultlang", description="Set the server's default language.")
    async def defaultlang(self, interaction: discord.Interaction, code: str):
        code = (code or "").lower()
        valid = {l["code"] for l in SUPPORTED_LANGUAGES}
        if code not in valid:
            return await interaction.response.send_message("❌ Unknown language code.", ephemeral=True)
        await database.set_server_lang(interaction.guild.id, code)
        e = discord.Embed(
            title="🌐 Server language updated",
            description=f"Default language is now **{label(code)}**.",
            color=COLOR
        ).set_footer(text=_footer_text())
        await interaction.response.send_message(embed=e, ephemeral=True)

    # /langlist (admin-only)
    @is_guild_admin()
    @app_commands.command(name="langlist", description="Show 50 supported languages.")
    async def langlist(self, interaction: discord.Interaction):
        items = []
        for l in SUPPORTED_LANGUAGES[:50]:
            items.append(f"{l.get('flag','')} **{l['code'].upper()}** — {l['name']}")
        e = discord.Embed(
            title="📋 Supported Languages (50)",
            description="\n".join(items),
            color=COLOR
        ).set_footer(text=_footer_text())
        await interaction.response.send_message(embed=e, ephemeral=True)

    # /settings — rich overview
    @is_guild_admin()
    @app_commands.command(name="settings", description="View current configuration.")
    async def settings(self, interaction: discord.Interaction):
        gid = interaction.guild.id

        server_lang = await database.get_server_lang(gid)
        bot_emote = await database.get_bot_emote(gid)
        err_ch = await database.get_error_channel(gid)
        allow = await database.get_translation_channels(gid)
        role_table = await database.get_role_table(gid)

        ch_display = "All channels" if allow is None else \
            (", ".join(f"<#{cid}>" for cid in allow) if allow else "No channels allowed")

        desc = (
            f"🌐 **Server language:** {label(server_lang) if server_lang else 'Not set'}\n"
            f"🙂 **Emote:** {bot_emote or 'Not set'}\n"
            f"🚨 **Error channel:** {(f'<#{err_ch}>' if err_ch else 'Not set')}\n"
            f"🧩 **Translate allow-list:** {ch_display}\n"
            f"🎖 **Level roles:** {'Installed' if role_table else 'Not installed'}"
        )

        e = discord.Embed(title="⚙️ Settings", description=desc, color=COLOR).set_footer(text=_footer_text())
        await interaction.response.send_message(embed=e, ephemeral=True)

    # /seterrorchannel (None to clear)
    @is_guild_admin()
    @app_commands.describe(channel="Error log channel (leave empty to clear)")
    @app_commands.command(name="seterrorchannel", description="Set or clear the error log channel.")
    async def seterrorchannel(self, interaction: discord.Interaction, channel: discord.TextChannel | None = None):
        gid = interaction.guild.id
        await database.set_error_channel(gid, channel.id if channel else None)
        msg = f"✅ Error channel {'set to ' + channel.mention if channel else 'cleared'}."
        await interaction.response.send_message(msg, ephemeral=True)

    # /setemote (already works; keep behavior)
    @is_guild_admin()
    @app_commands.describe(emote="Unicode or custom emote like <:name:id>")
    @app_commands.command(name="setemote", description="Set the reaction emote used to trigger translations.")
    async def setemote(self, interaction: discord.Interaction, emote: str):
        await database.set_bot_emote(interaction.guild.id, emote.strip())
        await interaction.response.send_message(f"✅ Emote set to {emote}.", ephemeral=True)

    # ----- Roles: setup/show/delete -----
    group = app_commands.Group(name="roles", description="Manage XP level roles")

    @group.command(name="setup", description="Create a 10-step level role ladder (Lv1–100).")
    @is_guild_admin()
    async def roles_setup(self, interaction: discord.Interaction):
        guild = interaction.guild
        await interaction.response.defer(ephemeral=True)
        # 10 bands: 1–10, 11–20, ... 91–100
        names = _make_role_names()
        colors = list(_ladder_colors(len(names)))
        mapping = []

        # Create from lowest to highest so top role ends up highest
        for i in range(10):
            ls = i * 10 + 1
            le = (i + 1) * 10
            name = names[i]
            color = colors[i]
            role = await guild.create_role(name=name, colour=discord.Colour(color), reason="Level ladder setup")
            mapping.append((ls, le, role.id))

        await database.upsert_role_table(guild.id, mapping)
        e = discord.Embed(
            title="🎖 Roles created",
            description="Created 10 level bands (Lv1–10 … Lv91–100).",
            color=COLOR
        ).set_footer(text=_footer_text())
        await interaction.followup.send(embed=e, ephemeral=True)

    @group.command(name="show", description="Show the current level role ladder.")
    @is_guild_admin()
    async def roles_show(self, interaction: discord.Interaction):
        mapping = await database.get_role_table(interaction.guild.id)
        if not mapping:
            return await interaction.response.send_message("No ladder installed.", ephemeral=True)
        lines = []
        for ls, le, rid in mapping:
            lines.append(f"Lv{ls:02d}–{le:02d} → <@&{rid}>")
        e = discord.Embed(title="🎖 Level Roles", description="\n".join(lines), color=COLOR).set_footer(text=_footer_text())
        await interaction.response.send_message(embed=e, ephemeral=True)

    @group.command(name="delete", description="Delete the ladder roles (and DB mapping).")
    @is_guild_admin()
    async def roles_delete(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        mapping = await database.get_role_table(interaction.guild.id)
        removed = 0
        if mapping:
            for _, _, rid in mapping:
                try:
                    role = interaction.guild.get_role(rid)
                    if role:
                        await role.delete(reason="Delete level ladder")
                        removed += 1
                except Exception:
                    pass
        await database.delete_role_table(interaction.guild.id)
        await interaction.followup.send(f"🗑 Deleted {removed} roles and cleared mapping.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCommands(bot))
