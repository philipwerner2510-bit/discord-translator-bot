from discord.ext import commands
import aiohttp
from googletrans import Translator as GoogleTranslator

class TranslateCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.google = GoogleTranslator()
        self.base_url = "https://libretranslate.com"

    async def translate_text(self, text: str, target_lang: str):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(f"{self.base_url}/translate", json={
                    "q": text,
                    "source": "auto",
                    "target": target_lang,
                    "format": "text"
                }) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("translatedText")
            except:
                pass
        # fallback to googletrans
        return self.google.translate(text, dest=target_lang).text

async def setup(bot):
    await bot.add_cog(TranslateCog(bot))
