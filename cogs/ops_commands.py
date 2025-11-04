import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from utils import database

class OpsCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, "start_time"):
            bot.start_time = datetime.utcnow()

    # ✅ OWNER ONLY COMMAND (your ID is whitelisted)
    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == 762267166031609858

    @app_commands.command(name="stats", description="Bot performance & AI usage statistics. (Owner Only)")
    async def stats_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        uptime = datetime.utcnow() - self.bot.start_time
        guilds = len(self.bot.guilds)
        users = len(set(user.id for guild in self.bot.guilds for user in guild.members))

        tokens_used, cost_used = await database.get_current_ai_usage()
        status = "🟢 Normal"

        if cost_used >= 10:
            status = "🔴 AI Disabled — Cap Reached"
        elif cost_used >= 8:
            status = "🟡 High Usage — Near Limit"

        embed = discord.Embed(
            title="📊 Demon Bot Status",
            color=0xde002a
        )
        embed.add_field(name="✅ Uptime", value=str(uptime).split('.')[0], inline=False)
        embed.add_field(name="🌍 Servers", value=str(guilds), inline=True)
        embed.add_field(name="👥 Users", value=str(users), inline=True)
        embed.add_field(name="🔁 Total Translations Today", value=str(self.bot.total_translations), inline=False)

        embed.add_field(name="🧠 AI Usage", value=f"{tokens_used:,} tokens", inline=True)
        embed.add_field(name="💸 Cost This Month", value=f"€{cost_used:.4f}", inline=True)
        embed.add_field(name="⚠️ Status", value=status, inline=False)

        embed.set_footer(text="Demon Translator © by Polarix1954 😈🔥")

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(OpsCommands(bot))