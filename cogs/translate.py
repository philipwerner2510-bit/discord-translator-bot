import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import json
import os
import re

from utils.database import database
from utils.logging_utils import log_error

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
AI_ENABLED = os.getenv("AI_ENABLED", "false").lower() == "true"

translator_url = os.getenv("LIBRE_SERVER_URL", "http://argostranslate:5000")

allowed_languages = {
    "en": "English",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "it": "Italian",
    "ru": "Russian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese"
}

async def ai_translate(text, target_lang):
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        resp = await client.responses.create(
            model=OPENAI_MODEL,
            input=f"Translate this to {allowed_languages.get(target_lang, target_lang)}:\n{text}",
        )
        return resp.output_text
    except Exception as e:
        print(f"[AI] Translation error: {e}")
        return None

async def libre_translate(text, target_lang):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{translator_url}/translate",
                json={"q": text, "source": "auto", "target": target_lang}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("translatedText")
    except Exception as e:
        print(f"[Libre] Error: {e}")
    return None

async def smart_translate(text, target_lang):
    # Try Libre → fallback to AI
    result = await libre_translate(text, target_lang)
    if result:
        return result

    if AI_ENABLED:
        return await ai_translate(text, target_lang)

    return None


class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("✅ Translate Cog Loaded")

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild:
            return
        if message.author.bot:
            return

        guild_id = message.guild.id
        allowed_channels = await database.get_translation_channels(guild_id)
        if not allowed_channels or message.channel.id not in allowed_channels:
            return

        # Skip links only
        if re.match(r"^https?://", message.content):
            return

        text = message.content.strip()
        if not text:
            return

        user_lang = await database.get_user_lang(message.author.id, guild_id)
        guild_lang = await database.get_guild_lang(guild_id)
        lang = user_lang or guild_lang or "en"

        translated = await smart_translate(text, lang)

        if translated:
            embed = discord.Embed(
                description=translated,
                color=discord.Color.blue()
            )
            embed.set_author(name=f"Translated → {allowed_languages.get(lang, lang)}")

            await message.reply(embed=embed, mention_author=False)

            try:
                await message.remove_reaction("✅", self.bot.user)
            except:
                pass
        else:
            await log_error(
                self.bot,
                guild_id,
                "Translation failed for a message (both engines).",
                None,
                admin_notify=True
            )


async def setup(bot):
    await bot.add_cog(Translate(bot))