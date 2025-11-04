import os
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
from utils import database

BOT_COLOR = 0xDE002A
PRIMARY_BASE = os.getenv("LIBRE_BASE", "https://libretranslate.com")  # switched default to .com
FALLBACKS = ["https://libretranslate.com", "https://translate.argosopentech.com", "https://libretranslate.de"]

def lang_url(base: str) -> str:
    return f"{base.rstrip('/')}/languages"

async def probe_libre(session: aiohttp.ClientSession, base: str):
    url = lang_url(base)
    async with session.get(url, headers={"Accept": "application/json"}, timeout=12, allow_redirects=True) as resp:
        ctype = resp.headers.get("Content-Type", "")
        if resp.status == 200 and "application/json" in ctype:
            return base, await resp.json()
        raise RuntimeError(f"status={resp.status} ctype={ctype}")

class Ops(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="stats", description="Show bot stats and AI usage.")
    async def stats_cmd(self, interaction: discord.Interaction):
        tokens, eur = await database.get_current_ai_usage()
        e = discord.Embed(title="📈 Bot Stats", color=BOT_COLOR)
        e.add_field(name="Translations (today)", value=str(getattr(self.bot, "total_translations", 0)), inline=True)
        e.add_field(name="Libre translations", value=str(getattr(self.bot, "libre_translations", 0)), inline=True)
        e.add_field(name="AI translations", value=str(getattr(self.bot, "ai_translations", 0)), inline=True)
        e.add_field(name="Cache hits", value=str(getattr(self.bot, "cache_hits", 0)), inline=True)
        e.add_field(name="Cache misses", value=str(getattr(self.bot, "cache_misses", 0)), inline=True)
        e.add_field(name="AI usage (tokens)", value=f"{tokens:,}", inline=True)
        e.add_field(name="AI cost (EUR est.)", value=f"€{eur:.4f}", inline=True)
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="librestatus", description="(Admin) Check Libre endpoint and languages.")
    @app_commands.checks.has_permissions(administrator=True)
    async def librestatus(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        tried = []
        try:
            async with aiohttp.ClientSession() as session:
                # Try env base first, then reasonable fallbacks
                for base in [PRIMARY_BASE, *[b for b in FALLBACKS if b != PRIMARY_BASE]]:
                    try:
                        good_base, data = await probe_libre(session, base)
                        langs = sorted({(x.get('code') or x.get('alpha2'), x.get('name'))
                                        for x in data if (x.get('code') or x.get('alpha2'))})
                        preview = ", ".join(sorted([c for c, _ in langs])[:30])
                        emb = discord.Embed(
                            title="🟢 Libre OK",
                            description=f"Endpoint: `{good_base}`\nLanguages: {len(langs)}\nCodes: {preview} …",
                            color=BOT_COLOR
                        )
                        if good_base != PRIMARY_BASE:
                            emb.set_footer(text=f"Note: primary `{PRIMARY_BASE}` failed; using fallback.")
                        return await interaction.followup.send(embed=emb, ephemeral=True)
                    except Exception as e:
                        tried.append(f"{base} ({type(e).__name__})")
                return await interaction.followup.send(
                    "❌ All Libre endpoints failed: " + " → ".join(tried),
                    ephemeral=True
                )
        except Exception as e:
            return await interaction.followup.send(f"❌ Libre check error: {type(e).__name__}: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Ops(bot))