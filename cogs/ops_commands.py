# cogs/ops_commands.py
import os
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from discord import app_commands
from utils import database
from utils.brand import COLOR, EMOJI_PRIMARY, EMOJI_HIGHLIGHT, EMOJI_ACCENT, footer

OWNER_ID = int(os.getenv("OWNER_ID", "762267166031609858"))

def owner_only_check(interaction: discord.Interaction) -> bool:
    return interaction.user and interaction.user.id == OWNER_ID

class Ops(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Owner-only /stats
    @app_commands.check(owner_only_check)
    @app_commands.command(name="stats", description="(Owner) Bot health, usage and counters.")
    async def stats_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # Uptime
        start_time = getattr(self.bot, "start_time", None)
        now = discord.utils.utcnow()
        if start_time is None:
            uptime_str = "—"
        else:
            delta: timedelta = now - start_time
            days, rem = divmod(delta.total_seconds(), 86400)
            hours, rem = divmod(rem, 3600)
            minutes, _ = divmod(rem, 60)
            uptime_str = f"{int(days)}d {int(hours)}h {int(minutes)}m"

        # Servers
        servers_count = len(self.bot.guilds)

        # Translation totals
        today_count, lifetime_count = await database.get_translation_totals()

        # AI usage (month)
        try:
            tokens, eur = await database.get_current_ai_usage()
        except Exception:
            tokens, eur = (0, 0.0)

        # Build embed
        e = discord.Embed(
            title=f"{EMOJI_HIGHLIGHT} Zephyra — System Stats",
            color=COLOR,
            description="Owner-only overview"
        )
        e.add_field(name="Uptime", value=f"`{uptime_str}`", inline=True)
        e.add_field(name="Servers", value=f"`{servers_count}`", inline=True)
        e.add_field(name="\u200b", value="\u200b", inline=True)

        e.add_field(
            name="Translations",
            value=f"**Today:** `{today_count:,}`\n**Lifetime:** `{lifetime_count:,}`",
            inline=True
        )
        e.add_field(
            name="AI Usage (month)",
            value=f"**Tokens:** `{tokens:,}`\n**Est. EUR:** `€{eur:,.2f}`",
            inline=True
        )
        e.add_field(name="\u200b", value="\u200b", inline=True)

        e.set_footer(text=footer())
        await interaction.followup.send(embed=e, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Ops(bot))