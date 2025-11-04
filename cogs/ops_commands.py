# cogs/ops_commands.py
import os
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
from utils import database

BOT_COLOR = 0xDE002A
LIBRE_BASE = os.getenv("LIBRE_BASE", "https://translate.argosopentech.com")
LIBRE_LANG_URL = f"{LIBRE_BASE.rstrip('/')}/languages"

class Ops(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="stats", description="Show bot stats and AI usage.")
    async def stats_cmd(self, interaction: discord.Interaction):
        tokens, eur = await database.get_current_ai_usage()
        embed = discord.Embed(title="📈 Bot Stats", color=BOT_COLOR)
        embed.add_field(name="Translations (today)", value=str(getattr(self.bot, "total_translations", 0)), inline=True)
        embed.add_field(name="Libre translations", value=str(getattr(self.bot, "libre_translations", 0)), inline=True)
        embed.add_field(name="AI translations", value=str(getattr(self.bot, "ai_translations", 0)), inline=True)
        embed.add_field(name="Cache hits", value=str(getattr(self.bot, "cache_hits", 0)), inline=True)
        embed.add_field(name="Cache misses", value=str(getattr(self.bot, "cache_misses", 0)), inline=True)
        embed.add_field(name="AI usage (tokens)", value=f"{tokens:,}", inline=True)
        embed.add_field(name="AI cost (EUR est.)", value=f"€{eur:.4f}", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="librestatus", description="(Admin) Check Libre/Argos endpoint and languages.")
    @app_commands.checks.has_permissions(administrator=True)
    async def librestatus(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    LIBRE_LANG_URL,
                    headers={"Accept": "application/json"},
                    timeout=12,
                    allow_redirects=True
                ) as resp:
                    ctype = resp.headers.get("Content-Type", "")
                    if resp.status != 200 or "application/json" not in ctype:
                        return await interaction.followup.send(
                            f"❌ Libre ping failed for {LIBRE_LANG_URL}\n"
                            f"status={resp.status}, content-type={ctype}\n"
                            "Tip: set **LIBRE_BASE** to a real API host "
                            "(e.g. `https://translate.argosopentech.com`).",
                            ephemeral=True
                        )
                    data = await resp.json()
        except Exception as e:
            return await interaction.followup.send(f"❌ Libre ping error: `{type(e).__name__}` — {e}", ephemeral=True)

        langs = sorted({(x.get('code') or x.get('alpha2'), x.get('name'))
                        for x in data if (x.get('code') or x.get('alpha2'))})
        preview = ", ".join(sorted([c for c, _ in langs])[:30])
        embed = discord.Embed(
            title="🟢 Libre/Argos OK",
            description=f"Endpoint: `{LIBRE_BASE}`\nLanguages: {len(langs)}\nCodes: {preview} …",
            color=BOT_COLOR
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Ops(bot))