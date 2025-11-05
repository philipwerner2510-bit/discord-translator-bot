# cogs/ops_commands.py
import os
import discord
from discord.ext import commands
from discord import app_commands
from utils import database
from datetime import datetime

OWNER_ID = int(os.getenv("OWNER_ID", "762267166031609858"))

def owner_only():
    async def predicate(interaction: discord.Interaction):
        return interaction.user.id == OWNER_ID
    return app_commands.check(predicate)

class Ops(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="stats", description="(Owner) Show AI usage and bot stats.")
    @owner_only()
    async def stats_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guilds = len(self.bot.guilds)
        users = sum(g.member_count or 0 for g in self.bot.guilds)

        tokens_in, tokens_out, eur = await database.get_month_ai_usage()  # month aggregate
        daily_trans, total_trans = await database.get_translation_totals()

        uptime = "—"
        if hasattr(self.bot, "start_time"):
            uptime = str(datetime.utcnow() - self.bot.start_time).split(".")[0]

        embed = discord.Embed(title="Zephyra • Stats (Owner)", color=0x00E6F6)
        embed.add_field(name="Servers", value=str(guilds))
        embed.add_field(name="Users (sum member_count)", value=str(users))
        embed.add_field(name="Uptime", value=uptime, inline=False)
        embed.add_field(name="AI Tokens (month)", value=f"in: {tokens_in:,} • out: {tokens_out:,}", inline=False)
        embed.add_field(name="AI Cost (est.)", value=f"€ {eur:.4f}", inline=True)
        embed.add_field(name="Translations", value=f"Today: {daily_trans:,} • Total: {total_trans:,}", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Ops(bot))