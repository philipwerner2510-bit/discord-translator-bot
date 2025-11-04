# cogs/user_commands.py
import os
import discord
from discord.ext import commands
from discord import app_commands
from utils import database
from utils.config import SUPPORTED_LANGS

OWNER_ID = int(os.getenv("OWNER_ID", "762267166031609858"))

class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.guild_only()
    @app_commands.describe(lang="Two-letter language code (e.g., en, de, fr)")
    @app_commands.command(name="setmylang", description="Set your personal translation language.")
    async def setmylang(self, interaction: discord.Interaction, lang: str):
        await interaction.response.defer(ephemeral=True)
        lang = lang.lower()
        if lang not in SUPPORTED_LANGS:
            await interaction.followup.send(f"❌ Invalid language. Supported: {', '.join(SUPPORTED_LANGS)}", ephemeral=True)
            return
        try:
            await database.set_user_lang(interaction.user.id, lang)
            await interaction.followup.send(f"✅ Your personal language has been set to `{lang}`.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error setting your language: {e}", ephemeral=True)

    @setmylang.autocomplete("lang")
    async def _setmylang_autocomplete(self, interaction: discord.Interaction, current: str):
        cur = (current or "").lower()
        return [app_commands.Choice(name=c, value=c) for c in SUPPORTED_LANGS if cur in c][:25]

    @app_commands.command(name="help", description="Show help for available commands.")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        in_guild = interaction.guild is not None
        is_admin = bool(in_guild and interaction.user.guild_permissions.administrator)
        is_owner = interaction.user.id == OWNER_ID

        embed = discord.Embed(
            title="📖 Demon Translator Help",
            description="List of available commands",
            color=0xDE002A
        )

        # Everyone
        embed.add_field(name="/setmylang `<lang>`",
                        value="Set your personal translation language (e.g. `en`, `de`, `fr`).",
                        inline=False)
        embed.add_field(name="/translate `<text>` `<target_lang>`",
                        value="Translate a specific text manually to a chosen language.",
                        inline=False)
        embed.add_field(name="/langlist",
                        value="Show all supported translation language codes.",
                        inline=False)
        embed.add_field(name="/test",
                        value="Quick check that the bot is responding to interactions.",
                        inline=False)

        # Admin-only (server managers)
        if is_admin:
            embed.add_field(name="🛠️ Admin Commands", value="*Only administrators can run these.*", inline=False)
            embed.add_field(name="/defaultlang `<lang>`", value="Set the server’s default translation language.", inline=False)
            embed.add_field(name="/channelselection", value="Select channels where the bot reacts to messages for translation.", inline=False)
            embed.add_field(name="/seterrorchannel `[channel]`", value="Set or clear the error logging channel.", inline=False)
            embed.add_field(name="/emote `<emote>`", value="Set the bot's reaction emote.", inline=False)
            embed.add_field(name="/settings", value="Show current server settings.", inline=False)
            embed.add_field(name="/config", value="Show current bot configuration & server wiring.", inline=False)
            embed.add_field(name="/stats", value="Show uptime, server count, and today's translations.", inline=False)

        # Owner-only (you)
        if is_owner:
            embed.add_field(name="👑 Owner Commands", value="*Visible only to the bot owner.*", inline=False)
            embed.add_field(name="/reloadconfig", value="Reload `config.json` without redeploy.", inline=False)
            embed.add_field(name="/exportdb", value="Export a SQLite DB backup file.", inline=False)

        embed.set_footer(text="Bot developed by Polarix1954")
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(UserCommands(bot))