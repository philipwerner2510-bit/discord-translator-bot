# cogs/ops_commands.py
import discord, aiohttp
from discord.ext import commands
from discord import app_commands
import os
from utils.brand import COLOR

LIBRE_BASE = os.getenv("LIBRE_BASE", "https://libretranslate.com")

class OpsCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="librestatus", description="Check Libre endpoint health.")
    async def librestatus(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        url = f"{LIBRE_BASE.rstrip('/')}/languages"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    ok = (resp.status == 200)
                    ctype = resp.headers.get("Content-Type","")
                    txt = await resp.text()
            embed = discord.Embed(title="Libre Status", color=COLOR)
            embed.add_field(name="URL", value=url, inline=False)
            embed.add_field(name="HTTP", value=str( resp.status ), inline=True)
            embed.add_field(name="Content-Type", value=ctype or "?", inline=True)
            embed.add_field(name="OK", value="✅" if ok else "❌", inline=True)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Libre ping failed: `{type(e).__name__}`", ephemeral=True)

async def setup(bot):
    await bot.add_cog(OpsCommands(bot))
