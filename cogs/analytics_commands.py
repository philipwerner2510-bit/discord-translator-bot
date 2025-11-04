# cogs/analytics_commands.py
import discord
from discord.ext import commands
from discord import app_commands
from utils import database

class AnalyticsCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="mystats", description="Your translation count.")
    async def mystats(self, interaction: discord.Interaction):
        count = await database.get_user_count(interaction.user.id)
        await interaction.response.send_message(f"📊 You translated `{count}` messages.", ephemeral=True)

    @app_commands.command(name="leaderboard", description="Top translators globally.")
    async def leaderboard(self, interaction: discord.Interaction):
        data = await database.get_top_users(10)
        if not data:
            return await interaction.response.send_message("📭 No stats yet.", ephemeral=True)
        desc = "\n".join([f"**<@{uid}>** — `{count}`" for uid, count in data])
        embed = discord.Embed(title="🌍 Global Leaderboard", description=desc, color=0xDE002A)
        await interaction.response.send_message(embed=embed)

    @app_commands.guild_only()
    @app_commands.command(name="guildstats", description="Server translation stats.")
    async def guildstats(self, interaction: discord.Interaction):
        count = await database.get_guild_count(interaction.guild.id)
        await interaction.response.send_message(f"📈 This server translated `{count}` messages.")

async def setup(bot):
    await bot.add_cog(AnalyticsCommands(bot))