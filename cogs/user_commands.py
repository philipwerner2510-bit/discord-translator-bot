import discord
from discord.ext import commands
from discord import app_commands
from utils import database

class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -----------------------
    # Set My Language
    # -----------------------
    @app_commands.command(name="setmylang", description="Set your personal translation language.")
    async def setmylang(self, interaction: discord.Interaction, lang: str):
        try:
            await interaction.response.defer(ephemeral=True)
            await database.set_user_lang(interaction.user.id, lang.lower())
            await interaction.followup.send(f"✅ Your personal language has been set to `{lang}`.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error setting your language: {e}", ephemeral=True)

    # -----------------------
    # Help Command
    # -----------------------
    @app_commands.command(name="help", description="Show help for available commands.")
    async def help(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)

            guild_id = interaction.guild.id if interaction.guild else None
            is_admin = interaction.guild_permissions.administrator if interaction.guild else False

            try:
                current_emote = await database.get_bot_emote(guild_id) if guild_id else "🔃"
            except Exception:
                current_emote = "🔃"

            embed = discord.Embed(
                title="📖 Demon Translator Help",
                description="Available commands:",
                color=0xde002a
            )

            # User commands
            embed.add_field(name="/setmylang <lang>", value="Set your personal translation language.", inline=False)
            embed.add_field(name="/translate <text> <target_lang>", value="Translate text manually.", inline=False)

            # Admin commands
            if is_admin:
                embed.add_field(name="🛠️ Admin Commands", value="Visible to administrators only.", inline=False)
                embed.add_field(name="/defaultlang <lang>", value="Set default server language.", inline=False)
                embed.add_field(name="/channelselection", value="Select channels for translation.", inline=False)
                embed.add_field(name="/seterrorchannel <channel>", value="Set error logging channel.", inline=False)
                embed.add_field(name=f"/emote <emote>", value=f"Set bot emote. Current: {current_emote}", inline=False)

            embed.set_footer(text="Bot developed by Polarix#1954")
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"❌ /help failed: {e}")

async def setup(bot):
    await bot.add_cog(UserCommands(bot))
