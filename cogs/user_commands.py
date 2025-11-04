import discord
from discord.ext import commands
from discord import app_commands
from utils import database
from utils.config import SUPPORTED_LANGS


OWNER_ID = 762267166031609858  # Polarix1954


class HelpView(discord.ui.View):
    def __init__(self, interaction_user):
        super().__init__(timeout=120)
        self.interaction_user = interaction_user

    async def switch(self, interaction, embed_func):
        if interaction.user.id != self.interaction_user.id:
            return await interaction.response.defer()
        await interaction.response.edit_message(embed=embed_func(), view=self)

    @discord.ui.button(label="General", style=discord.ButtonStyle.primary)
    async def general_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch(interaction, embed_general)

    @discord.ui.button(label="Admin", style=discord.ButtonStyle.secondary)
    async def admin_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch(interaction, embed_admin)

    @discord.ui.button(label="Owner", style=discord.ButtonStyle.danger)
    async def owner_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch(interaction, embed_owner)


def embed_general():
    embed = discord.Embed(
        title="📖 Demon Translator – General Commands",
        color=0xDE002A
    )
    embed.add_field(name="/setmylang `<lang>`", value="Set your personal translation language.", inline=False)
    embed.add_field(name="/translate `<text>` `<lang>`", value="Translate any text manually.", inline=False)
    embed.add_field(name="/langlist", value="List supported languages.", inline=False)
    embed.add_field(name="/leaderboard", value="Show top translators.", inline=False)
    embed.add_field(name="/mystats", value="Your translation activity stats.", inline=False)
    embed.add_field(name="/guildstats", value="Server translation stats.", inline=False)
    embed.add_field(name="/test", value="Check if the bot is alive.", inline=False)
    embed.add_field(name="/ping", value="Check bot response speed.", inline=False)
    embed.set_footer(text="Created by Polarix1954 😈")
    return embed


def embed_admin():
    embed = discord.Embed(
        title="🛠 Admin Commands",
        description="Administrator permissions required.",
        color=0xDE002A
    )
    embed.add_field(name="/defaultlang `<lang>`", value="Set server default language.", inline=False)
    embed.add_field(name="/channelselection", value="Select reaction-enabled channels.", inline=False)
    embed.add_field(name="/seterrorchannel", value="Set or remove error channel.", inline=False)
    embed.add_field(name="/emote `<emoji>`", value="Set bot reaction emoji.", inline=False)
    embed.add_field(name="/settings", value="Show server bot configuration.", inline=False)
    embed.add_field(name="/config", value="Show bot configuration overview.", inline=False)
    embed.add_field(name="/stats", value="Server and bot performance stats.", inline=False)
    return embed


def embed_owner():
    embed = discord.Embed(
        title="👑 Owner Commands",
        description="Reserved for Polarix1954",
        color=0xDE002A
    )
    embed.add_field(name="/reloadconfig", value="Reload config.json without restart.", inline=False)
    embed.add_field(name="/exportdb", value="Export a database backup.", inline=False)
    return embed


class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ✅ /help
    @app_commands.command(name="help", description="Show help for Demon Translator.")
    async def help_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=embed_general(),
            view=HelpView(interaction.user),
            ephemeral=True
        )

    # ✅ /test
    @app_commands.command(name="test", description="Check if the bot is responsive.")
    async def test_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "✅ Demon Bot is alive and lurking in the shadows 😈",
            ephemeral=True
        )

    # ✅ /ping
    @app_commands.command(name="ping", description="Check bot ping.")
    async def ping_cmd(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(
            f"🏓 Pong! `{latency}ms`",
            ephemeral=True
        )

    # ✅ /setmylang
    @app_commands.command(name="setmylang", description="Set your personal translation language.")
    async def setmylang(self, interaction: discord.Interaction, lang: str):
        lang = lang.lower()
        if lang not in SUPPORTED_LANGS:
            return await interaction.response.send_message(
                f"❌ Unsupported: `{lang}`\nUse `/langlist`",
                ephemeral=True
            )
        await database.set_user_lang(interaction.user.id, lang)
        await interaction.response.send_message(
            f"✅ Language set to `{lang}`",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(UserCommands(bot))