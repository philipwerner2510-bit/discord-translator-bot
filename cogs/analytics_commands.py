# cogs/analytics_commands.py
import discord
from discord.ext import commands
from discord import app_commands
from utils import database

BRAND_COLOR = 0x00E6F6  # Zephyra cyan

class Analytics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="Show global translation activity (today & lifetime).")
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # We don’t keep per-user rankings yet (no schema for it).
        # Show global activity using existing counters.
        today, total = await database.get_translation_totals()

        embed = discord.Embed(
            title="Zephyra — Global Activity",
            color=BRAND_COLOR,
            description="(Per-user leaderboard coming soon)"
        )
        embed.add_field(name="Today", value=f"**{today:,}** translations", inline=True)
        embed.add_field(name="Lifetime", value=f"**{total:,}** translations", inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Analytics(bot))