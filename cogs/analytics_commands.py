import discord
from discord.ext import commands
from discord import app_commands
from utils import database

BOT_COLOR = 0xDE002A

class Analytics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="Top translators (all-time).")
    async def leaderboard(self, interaction: discord.Interaction):
        rows = await database.top_translators(10)
        if not rows:
            return await interaction.response.send_message("No data yet. Translate something first!", ephemeral=True)
        desc = []
        for rank, (uid, count) in enumerate(rows, 1):
            user = interaction.client.get_user(uid) or (await interaction.client.fetch_user(uid))
            name = user.name if user else f"User {uid}"
            desc.append(f"**{rank}.** {name} — **{count}**")
        embed = discord.Embed(title="🏆 Top Translators", description="\n".join(desc), color=BOT_COLOR)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Analytics(bot))