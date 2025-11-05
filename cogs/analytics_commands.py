import discord
from discord.ext import commands
from discord import app_commands
from utils.brand import COLOR, footer, Z_EXCITED, Z_TIRED
from utils import database

class Analytics(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="leaderboard", description="Top translators in this server.")
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        gid = interaction.guild.id if interaction.guild else None
        rows = await database.get_leaderboard(gid, 10)
        if not rows:
            e = discord.Embed(description=f"{Z_TIRED} No data yet. Be the first to translate!", color=COLOR)
            e.set_footer(text=footer()); return await interaction.followup.send(embed=e)

        lines = []
        for i,(uid,count) in enumerate(rows, start=1):
            member = interaction.guild.get_member(uid) or f"<@{uid}>"
            name = member.display_name if hasattr(member, "display_name") else str(member)
            lines.append(f"**#{i}** — **{name}** • `{count}` translations")

        e = discord.Embed(title=f"{Z_EXCITED} Server Leaderboard", description="\n".join(lines), color=COLOR)
        e.set_footer(text=footer()); await interaction.followup.send(embed=e)

    @app_commands.command(name="stats", description="Show bot status.")
    async def stats(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guilds = len(self.bot.guilds)
        latency = round(self.bot.latency * 1000)
        e = discord.Embed(title="Bot Stats", color=COLOR,
                          description=f"• Guilds: **{guilds}**\n• Latency: **{latency} ms**")
        e.set_footer(text=footer()); await interaction.followup.send(embed=e, ephemeral=True)

async def setup(bot): await bot.add_cog(Analytics(bot))
