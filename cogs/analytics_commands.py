# cogs/analytics_commands.py
import discord
from discord.ext import commands
from discord import app_commands
from utils import database
from utils.brand import COLOR, EMOJI_PRIMARY, EMOJI_HIGHLIGHT, EMOJI_ACCENT, footer

class Analytics(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="Global translation activity (today & lifetime).")
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # For now we only show global totals (per-user LB planned later)
        today, total = await database.get_translation_totals()

        e = discord.Embed(
            title=f"{EMOJI_PRIMARY} Zephyra — Global Activity",
            color=COLOR,
            description="(Per-user leaderboard coming soon)"
        )
        e.add_field(name="Today", value=f"**{today:,}** translations", inline=True)
        e.add_field(name="Lifetime", value=f"**{total:,}** translations", inline=True)
        e.add_field(name="\u200b", value="\u200b", inline=True)
        e.set_footer(text=footer())

        await interaction.followup.send(embed=e, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Analytics(bot))