import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from utils import database

OWNER_ID = 762267166031609858
BOT_COLOR = 0xde002a

class OpsCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, "start_time"):
            bot.start_time = datetime.utcnow()

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == OWNER_ID

    @app_commands.command(name="stats", description="Bot performance & AI usage statistics. (Owner Only)")
    async def stats_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        uptime = datetime.utcnow() - self.bot.start_time
        guilds = len(self.bot.guilds)
        users = len({m.id for g in self.bot.guilds for m in g.members})

        tokens_used, eur_used = await database.get_current_ai_usage()

        hits = getattr(self.bot, "cache_hits", 0)
        misses = getattr(self.bot, "cache_misses", 0)
        cached = getattr(self.bot, "cached_translations", 0)
        ai_count = getattr(self.bot, "ai_translations", 0)
        libre_count = getattr(self.bot, "libre_translations", 0)
        total = getattr(self.bot, "total_translations", 0)

        denom = hits + misses
        hit_rate = (hits / denom * 100.0) if denom else 0.0

        status = "🟢 Normal"
        if eur_used >= 10:
            status = "🔴 AI Disabled — Cap Reached"
        elif eur_used >= 8:
            status = "🟡 High Usage — Near Limit"

        embed = discord.Embed(title="📊 Demon Bot Status", color=BOT_COLOR)
        embed.add_field(name="✅ Uptime", value=str(uptime).split('.')[0], inline=False)
        embed.add_field(name="🌍 Servers", value=str(guilds), inline=True)
        embed.add_field(name="👥 Users", value=str(users), inline=True)
        embed.add_field(name="🔁 Translations (session)", value=str(total), inline=False)

        # Cache section
        embed.add_field(name="🗄️ Cache Hits", value=f"{hits}", inline=True)
        embed.add_field(name="🚫 Cache Misses", value=f"{misses}", inline=True)
        embed.add_field(name="🎯 Hit Rate", value=f"{hit_rate:.1f}%", inline=True)

        # Engine breakdown (session)
        embed.add_field(name="🧠 AI (session)", value=f"{ai_count}", inline=True)
        embed.add_field(name="🆓 Libre (session)", value=f"{libre_count}", inline=True)
        embed.add_field(name="💾 Returned from Cache", value=f"{cached}", inline=True)

        # AI billing
        embed.add_field(name="🧠 AI Tokens (month)", value=f"{tokens_used:,}", inline=True)
        embed.add_field(name="💸 AI Cost (month)", value=f"€{eur_used:.4f}", inline=True)
        embed.add_field(name="⚠️ Status", value=status, inline=True)

        embed.set_footer(text="Demon Translator © by Polarix1954 😈🔥")
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(OpsCommands(bot))