# cogs/analytics_commands.py
import discord
from discord.ext import commands
from discord import app_commands

from utils.brand import COLOR, footer
from utils.database import get_user_lang, get_translation_channels

# Optional analytics logger (no-op if not present)
try:
    from utils.logging_utils import log_analytics_event  # type: ignore
except Exception:
    async def log_analytics_event(*args, **kwargs):
        return None


class AnalyticsCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="stats", description="Show server translation configuration stats.")
    @app_commands.guild_only()
    async def stats(self, interaction: discord.Interaction):
        gid = interaction.guild.id
        lang = await get_user_lang(interaction.user.id) or "not set"
        channels = await get_translation_channels(gid)
        channel_count = len(channels) if channels else "All channels"

        e = discord.Embed(
            title="📊 Server Analytics",
            description=(
                f"**Your preferred language:** `{lang}`\n"
                f"**Translation channels:** `{channel_count}`"
            ),
            color=COLOR,
        )
        e.set_footer(text=footer())

        await interaction.response.send_message(embed=e, ephemeral=False)

        # Fire-and-forget analytics (if available)
        try:
            await log_analytics_event(gid, interaction.user.id, "stats_used")
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(AnalyticsCommands(bot))
