# cogs/analytics_commands.py
import discord
from discord.ext import commands
from discord import app_commands
from utils.brand import COLOR
from utils import database

class Analytics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="stats", description="Show usage statistics.")
    async def stats_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        total = getattr(self.bot, "total_translations", 0)
        libre = getattr(self.bot, "libre_translations", 0)
        ai = getattr(self.bot, "ai_translations", 0)
        cache_hits = getattr(self.bot, "cache_hits", 0)
        cache_miss = getattr(self.bot, "cache_misses", 0)
        try:
            tokens, eur = await database.get_current_ai_usage()
        except Exception:
            tokens, eur = 0, 0.0
        embed = discord.Embed(title="Stats", color=COLOR)
        embed.add_field(name="Translations (today)", value=str(total), inline=True)
        embed.add_field(name="AI / Libre", value=f"{ai} / {libre}", inline=True)
        embed.add_field(name="Cache (hit/miss)", value=f"{cache_hits} / {cache_miss}", inline=True)
        embed.add_field(name="AI usage", value=f"{tokens} tokens ~ €{eur:.2f}", inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="leaderboard", description="Top translators in this server.")
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        gid = interaction.guild.id if interaction.guild else 0
        top = await database.get_guild_leaderboard(gid, limit=10)
        if not top:
            return await interaction.followup.send("No data yet.", ephemeral=True)
        lines = []
        for rank, (uid, count) in enumerate(top, start=1):
            member = interaction.guild.get_member(uid)
            name = member.display_name if member else f"User {uid}"
            lines.append(f"**#{rank}** — {name}: **{count}**")
        embed = discord.Embed(title="Leaderboard", description="\n".join(lines), color=COLOR)
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Analytics(bot))
