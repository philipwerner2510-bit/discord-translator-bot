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

    # -----------------------
    # /setmylang
    # -----------------------
    @app_commands.guild_only()
    @app_commands.describe(lang="Two-letter language code (e.g., en, de, fr)")
    @app_commands.command(name="setmylang", description="Set your personal translation language.")
    async def setmylang(self, interaction: discord.Interaction, lang: str):
        await interaction.response.defer(ephemeral=True)
        lang = (lang or "").lower()
        if lang not in SUPPORTED_LANGS:
            return await interaction.followup.send(
                f"❌ Invalid language. Supported: {', '.join(SUPPORTED_LANGS)}", ephemeral=True
            )
        await database.set_user_lang(interaction.user.id, lang)
        await interaction.followup.send(f"✅ Set language to `{lang}`.", ephemeral=True)

    @setmylang.autocomplete("lang")
    async def _lang_auto(self, interaction: discord.Interaction, current: str):
        cur = (current or "").lower()
        return [app_commands.Choice(name=c, value=c) for c in SUPPORTED_LANGS if cur in c][:25]

    # -----------------------
    # /help (tabbed with buttons)
    # -----------------------
    @app_commands.command(name="help", description="Show help for commands.")
    async def help(self, interaction: discord.Interaction):
        is_admin = bool(interaction.guild and interaction.user.guild_permissions.administrator)
        is_owner = interaction.user.id == OWNER_ID

        def embed_general():
            e = discord.Embed(title="📖 Help — General", color=0xDE002A)
            e.add_field(name="/setmylang `<lang>`", value="Set your personal translation language.", inline=False)
            e.add_field(name="/translate `<text>` `<target_lang>`", value="Translate text manually.", inline=False)
            e.add_field(name="/leaderboard", value="Top translators (server/global).", inline=False)
            e.add_field(name="/mystats", value="Your translation count in this server.", inline=False)
            e.add_field(name="/guildstats", value="Server total translations.", inline=False)
            e.add_field(name="/langlist", value="Show supported language codes.", inline=False)
            e.add_field(name="/test", value="Check that the bot responds.", inline=False)
            e.set_footer(text="Bot developed by Polarix1954")
            return e

        def embed_admin():
            e = discord.Embed(title="🛠️ Help — Admin", color=0xDE002A)
            e.add_field(name="/defaultlang `<lang>`", value="Set server default language.", inline=False)
            e.add_field(name="/channelselection", value="Pick channels for reaction-to-translate.", inline=False)
            e.add_field(name="/seterrorchannel `[channel]`", value="Set/clear error logging channel.", inline=False)
            e.add_field(name="/emote `<emote>`", value="Set reaction emoji the bot listens for.", inline=False)
            e.add_field(name="/settings", value="View current server settings.", inline=False)
            e.add_field(name="/config", value="Show config & wiring details.", inline=False)
            e.add_field(name="/stats", value="Uptime, servers, translations today.", inline=False)
            e.set_footer(text="Bot developed by Polarix1954")
            return e

        def embed_owner():
            e = discord.Embed(title="👑 Help — Owner", color=0xDE002A)
            e.add_field(name="/reloadconfig", value="Reload `config.json` without redeploy.", inline=False)
            e.add_field(name="/exportdb", value="Export a DB backup file.", inline=False)
            e.set_footer(text="Bot developed by Polarix1954")
            return e

        class HelpView(discord.ui.View):
            def __init__(self, is_admin: bool, is_owner: bool):
                super().__init__(timeout=120)
                self._is_admin = is_admin
                self._is_owner = is_owner
                # Disable buttons the user can't use
                for child in self.children:
                    if isinstance(child, discord.ui.Button):
                        if child.label == "Admin" and not is_admin:
                            child.disabled = True
                        if child.label == "Owner" and not is_owner:
                            child.disabled = True

            @discord.ui.button(label="General", style=discord.ButtonStyle.primary)
            async def btn_general(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.edit_message(embed=embed_general(), view=self)

            @discord.ui.button(label="Admin", style=discord.ButtonStyle.secondary)
            async def btn_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
                if not self._is_admin:
                    return await interaction.response.defer()
                await interaction.response.edit_message(embed=embed_admin(), view=self)

            @discord.ui.button(label="Owner", style=discord.ButtonStyle.danger)
            async def btn_owner(self, interaction: discord.Interaction, button: discord.ui.Button):
                if not self._is_owner:
                    return await interaction.response.defer()
                await interaction.response.edit_message(embed=embed_owner(), view=self)

        await interaction.response.send_message(
            embed=embed_general(),
            view=HelpView(is_admin, is_owner),
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(UserCommands(bot))