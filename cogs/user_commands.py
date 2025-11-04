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
    @app_commands.command(name="setmylang", description="Set your personal translation language.")
    async def setmylang(self, interaction: discord.Interaction, lang: str):
        await interaction.response.defer(ephemeral=True)
        lang = lang.lower()
        if lang not in SUPPORTED_LANGS:
            return await interaction.followup.send(
                f"❌ Invalid language. Supported: {', '.join(SUPPORTED_LANGS)}", ephemeral=True)
        await database.set_user_lang(interaction.user.id, lang)
        await interaction.followup.send(f"✅ Set language to `{lang}`.", ephemeral=True)

    @setmylang.autocomplete("lang")
    async def _lang_auto(self, interaction: discord.Interaction, current: str):
        current = (current or "").lower()
        return [app_commands.Choice(name=c, value=c)
                for c in SUPPORTED_LANGS if current in c][:25]

    @app_commands.command(name="help", description="Show help for commands.")
    async def help(self, interaction: discord.Interaction):
        is_admin = bool(interaction.guild and interaction.user.guild_permissions.administrator)
        is_owner = interaction.user.id == OWNER_ID

        def embed_general():
            e = discord.Embed(title="📖 Help — General", color=0xDE002A)
            e.add_field(name="/setmylang", value="Set your personal language.", inline=False)
            e.add_field(name="/translate", value="Translate text manually.", inline=False)
            e.add_field(name="/leaderboard", value="Top translators.", inline=False)
            e.add_field(name="/mystats", value="Your translations here.", inline=False)
            e.add_field(name="/guildstats", value="Server total translations.", inline=False)
            e.add_field(name="/langlist", value="Show supported languages.", inline=False)
            e.add_field(name="/test", value="Ping interaction.", inline=False)
            e.set_footer(text="Bot developed by Polarix1954")
            return e

        def embed_admin():
            e = discord.Embed(title="🛠️ Help — Admin", color=0xDE002A)
            e.add_field(name="/defaultlang", value="Set server default language.", inline=False)
            e.add_field(name="/channelselection", value="Select translation channels.", inline=False)
            e.add_field(name="/seterrorchannel", value="Set/clear error channel.", inline=False)
            e.add_field(name="/emote", value="Set reaction emoji.", inline=False)
            e.add_field(name="/settings", value="Show server settings.", inline=False)
            e.add_field(name="/config", value="Bot config overview.", inline=False)
            e.add_field(name="/stats", value="Uptime + totals.", inline=False)
            e.set_footer(text="Bot developed by Polarix1954")
            return e

        def embed_owner():
            e = discord.Embed(title="👑 Help — Owner", color=0xDE002A)
            e.add_field(name="/reloadconfig", value="Reload conf without redeploy.", inline=False)
            e.add_field(name="/exportdb", value="Export DB backup.", inline=False)
            e.set_footer(text="Bot developed by Polarix1954")
            return e

        class HelpView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=120)
            @discord.ui.button(label="General", style=discord.ButtonStyle.primary)
            async def g(self, _, it):
                await it.response.edit_message(embed=embed_general(), view=self)
            @discord.ui.button(label="Admin", style=discord.ButtonStyle.secondary, disabled=not is_admin)
            async def a(self, _, it):
                await it.response.edit_message(embed=embed_admin(), view=self)
            @discord.ui.button(label="Owner", style=discord.ButtonStyle.danger, disabled=not is_owner)
            async def o(self, _, it):
                await it.response.edit_message(embed=embed_owner(), view=self)

        await interaction.response.send_message(embed=embed_general(), view=HelpView(), ephemeral=True)

async def setup(bot):
    await bot.add_cog(UserCommands(bot))