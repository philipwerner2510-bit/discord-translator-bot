# cogs/ops_commands.py
import discord
from discord.ext import commands
from discord import app_commands

try:
    from utils.brand import COLOR, footer_text
except Exception:
    COLOR = 0x00E6F6
    def footer_text(): return "Zephyra"

class Ops(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Latency check.")
    async def ping(self, interaction: discord.Interaction):
        latency_ms = round(self.bot.latency * 1000)
        e = discord.Embed(title="🏁 Pong!", description=f"Gateway latency: **{latency_ms} ms**", color=COLOR)
        e.set_footer(text=footer_text())
        await interaction.response.send_message(embed=e, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Ops(bot))
