import discord
from discord.ext import commands
from discord import app_commands
from utils import database

class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -----------------------
    # Set My Language (per user)
    # -----------------------
    @app_commands.command(name="setmylang", description="Set your personal translation language.")
    async def setmylang(self, interaction: discord.Interaction, lang: str):
        await interaction.response.defer(ephemeral=True)
        try:
            await database.set_user_lang(interaction.user.id, lang.lower())
            await interaction.followup.send(f"✅ Your personal language has been set to `{lang}`.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error setting your language: {e}", ephemeral=True)

    # -----------------------
    # Help command
    # -----------------------
    @app_commands.command(name="help", description="Show help for available commands.")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        is_admin = interaction.user.guild_permissions.administrator
        guild_id = interaction.guild.id if interaction.guild else None

        embed = discord.Embed(
            title="📖 Demon Translator Help",
            description="List of available commands",
            color=0xde002a
        )

        # Commands for all users
        embed.add_field(
            name="/setmylang `<lang>`",
            value="Set your personal translation language (e.g. `en`, `de`, `fr`).\n"
                  "This overrides the server default language.",
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
                value="*These commands are only visible to administrators.*",
                inline=False
            )
            embed.add_field(
                name="/defaultlang `<lang>`",
                value="Set the **default translation language** for the server.",
                inline=False
            )
            embed.add_field(
                name="/channelselection",
                value="Select one or multiple channels where the bot will react to messages for translation.",
                inline=False
            )
            embed.add_field(
                name="/seterrorchannel `<channel>` or `none`",
                value="Define the error logging channel for your server or remove it by passing `none`.",
                inline=False
            )
            embed.add_field(
                name="/emote `<emote>`",
                value="Set the bot's reaction emote for translation channels.",
                inline=False
            )
            embed.add_field(
                name="/settings",
                value="Show current server settings: default language, emote, error channel, and translation channels.",
                inline=False
            )
            embed.add_field(
                name="/langlist",
                value="Show all supported translation languages with flags, codes, and names.",
                inline=False
            )

        embed.set_footer(text="Bot developed by Polarix#1954")

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(UserCommands(bot))
