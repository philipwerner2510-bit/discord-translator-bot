import discord
from discord.ext import commands
from discord import app_commands
from utils import database
import aiohttp

LIBRE_URL = "https://libretranslate.de/translate"

class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -----------------------
    # Translate Slash Command
    # -----------------------
    @app_commands.command(name="translate", description="Translate a specific text manually.")
    async def translate(self, interaction: discord.Interaction, text: str, target_lang: str):
        await interaction.response.defer(ephemeral=True)
        try:
            translated_text, detected = await self.translate_text(text, target_lang)
            embed = discord.Embed(
                title="🌐 Translation",
                color=0xde002a
            )
            embed.set_footer(text=f"Detected language: {detected} | Translated to: {target_lang}")
            await interaction.followup.send(embed=embed)
            await interaction.followup.send(translated_text)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    # -----------------------
    # Translation helper
    # -----------------------
    async def translate_text(self, text: str, target_lang: str):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                LIBRE_URL, 
                json={"q": text, "source": "auto", "target": target_lang}
            ) as resp:
                data = await resp.json()
                return data["translatedText"], data.get("detectedLanguage", "unknown")

async def setup(bot):
    await bot.add_cog(Translate(bot))
