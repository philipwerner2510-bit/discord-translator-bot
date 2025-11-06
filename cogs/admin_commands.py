# cogs/admin_commands.py
import discord
from discord.ext import commands
from discord import app_commands

from utils.brand import COLOR, footer_text, NAME
from utils import database
from utils.language_data import label


def _need_admin():
    def check(interaction: discord.Interaction):
        return interaction.user.guild_permissions.manage_guild
    return app_commands.check(check)


class AdminCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # /settings — show current server config snapshot
    @app_commands.command(name="settings", description="Show server settings.")
    @_need_admin()
    @app_commands.guild_only()
    async def settings(self, interaction: discord.Interaction):
        gid = interaction.guild.id
        server_lang = await database.get_server_lang(gid)
        allow = await database.get_translation_channels(gid)
        emote = await database.get_bot_emote(gid)

        lines = [
            f"**Server Language:** {label(server_lang) if server_lang else '(not set)'}",
            f"**Translate Mode:** {'Allow-list' if allow else 'All channels'}",
            f"**Allowed Channels:** {len(allow) if allow else '—'}",
            f"**Reaction Emote:** {emote or '🔃'}",
        ]
        e = discord.Embed(
            title=f"{NAME} — Server Settings",
            description="\n".join(lines),
            color=COLOR
        ).set_footer(text=footer_text)
        await interaction.response.send_message(embed=e, ephemeral=True)

    # roles group
    roles = app_commands.Group(name="roles", description="Level role management")

    @roles.command(name="setup", description="Create level roles (Lv.1–100) in steps and color gradient.")
    @_need_admin()
    @app_commands.guild_only()
    async def roles_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            created_count = await database.create_role_table(interaction.guild)
            e = discord.Embed(
                description=f"Created or updated **{created_count}** level roles.",
                color=COLOR
            ).set_footer(text=footer_text)
            await interaction.followup.send(embed=e, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(
                embed=discord.Embed(description=f"Failed: `{e}`", color=COLOR).set_footer(text=footer_text),
                ephemeral=True
            )

    @roles.command(name="show", description="Show configured level roles.")
    @_need_admin()
    @app_commands.guild_only()
    async def roles_show(self, interaction: discord.Interaction):
        mapping = await database.get_role_table(interaction.guild.id)
        if not mapping:
            return await interaction.response.send_message(
                embed=discord.Embed(description="No level roles configured.", color=COLOR).set_footer(text=footer_text),
                ephemeral=True
            )
        lines = []
        for lvl in sorted(mapping.keys()):
            rid = mapping[lvl]
            role = interaction.guild.get_role(rid)
            if role:
                lines.append(f"Lv.{lvl:>3} → {role.mention}")
        e = discord.Embed(
            title="Level Roles",
            description="\n".join(lines) if lines else "(roles missing on server)",
            color=COLOR
        ).set_footer(text=footer_text)
        await interaction.response.send_message(embed=e, ephemeral=True)

    @roles.command(name="delete", description="Delete all level roles created by the bot.")
    @_need_admin()
    @app_commands.guild_only()
    async def roles_delete(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        removed = await database.delete_role_table(interaction.guild)
        e = discord.Embed(
            description=f"Removed **{removed}** level roles.",
            color=COLOR
        ).set_footer(text=footer_text)
        await interaction.followup.send(embed=e, ephemeral=True)

    @app_commands.command(name="setemote", description="Set the reaction emoji Zephyra uses for DM translations.")
    @_need_admin()
    @app_commands.guild_only()
    @app_commands.describe(emoji="Unicode like 🔃 or custom like <:name:1234567890>")
    async def setemote(self, interaction: discord.Interaction, emoji: str):
        emoji = (emoji or "").strip()
        await database.set_bot_emote(interaction.guild.id, emoji)
        e = discord.Embed(
            description=f"Reaction emoji updated to {emoji}.",
            color=COLOR
        ).set_footer(text=footer_text)
        await interaction.response.send_message(embed=e, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCommands(bot))
