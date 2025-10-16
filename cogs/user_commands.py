import discord
from discord.ext import commands
from discord import app_commands
from utils import database

class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setmylang", description="Set your personal translation language.")
    async def setmylang(self, interaction: discord.Interaction, lang: str):
        await interaction.response.defer(ephemeral=True)
        try:
            await database.set_user_lang(interaction.user.id, lang.lower())
            await interaction.followup.send(f"✅ Your personal language has been set to `{lang}`.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error setting your language: {e}", ephemeral=True)

    @app_commands.command(name="help", description="Show help for available commands.")
    async def help(self, interaction: discord.Interaction):
        is_admin = interaction.user.guild_permissions.administrator

        embed = discord.Embed(
            title="📖 Demon Translator Help",
            description="List of available commands",
            color=0xde002a
        )

        # Commands everyone can use
        embed.add_field(
            name="/setmylang `<lang>`",
            value="Set your personal translation language (e.g. `en`, `de`, `fr`). Overrides server default.",
            inline=False
        )
        embed.add_field(
            name="/translate `<text>` `<target_lang>`",
            value="Translate a specific text manually to a chosen language.",
            inline=False
        )

        # Admin-only commands
        if is_admin:
            embed.add_field(
                name="🛠️ Admin Commands",
                value="*Visible only to administrators.*",
                inline=False
            )
            embed.add_field(
                name="/defaultlang `<lang>`",
                value="Set the server's default translation language.",
                inline=False
            )
            embed.add_field(
                name="/channelselection",
                value="Select one or multiple channels where the bot will react for translations.",
                inline=False
            )
            embed.add_field(
                name="/seterrorchannel `<channel>`",
                value="Set the channel for error logging.",
                inline=False
            )

        embed.set_footer(text="Bot developed by Polarix#1954")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(UserCommands(bot))
