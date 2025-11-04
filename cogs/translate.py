import discord
import aiohttp
import asyncio
from discord.ext import commands
from discord import app_commands, ui, SelectOption
from utils import database
from utils.logging_utils import log_error
from utils.cache import TranslationCache
from datetime import datetime
from openai import OpenAI

# Load env
import os

CLIENT = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

LIBRE_URL = os.getenv("ARGOS_URL", "http://localhost:5000/translate")

SUPPORTED_LANGS = {
    "en": "🇬🇧 English",
    "de": "🇩🇪 German",
    "fr": "🇫🇷 French",
    "es": "🇪🇸 Spanish",
    "it": "🇮🇹 Italian",
    "pt": "🇵🇹 Portuguese",
    "ru": "🇷🇺 Russian",
    "ja": "🇯🇵 Japanese",
    "zh": "🇨🇳 Chinese",
    "ar": "🇸🇦 Arabic",
    "ko": "🇰🇷 Korean",
    "tr": "🇹🇷 Turkish",
    "nl": "🇳🇱 Dutch"
}

cache = TranslationCache(ttl=600)  # 10 min cache


def normalize_emote_input(s: str):
    return s.strip() if s else "🔁"


class LangSelect(ui.Select):
    def __init__(self):
        options = [
            SelectOption(label=v, value=k)
            for k, v in SUPPORTED_LANGS.items()
        ]
        super().__init__(placeholder="Pick language…", options=options[:25], min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        lang = self.values[0]
        await database.set_user_lang(interaction.user.id, lang)
        await interaction.response.send_message(
            f"✅ Saved! Your translation language is now **{SUPPORTED_LANGS[lang]}**",
            ephemeral=True
        )


class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --------------------------------
    # React To Translate
    # --------------------------------
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot or reaction.message.guild is None:
            return

        msg = reaction.message
        gid = msg.guild.id

        bot_emote = normalize_emote_input(await database.get_bot_emote(gid))
        if str(reaction.emoji) != bot_emote:
            return

        try:
            await self.translate_reaction(msg, user)
            try:
                await reaction.remove(user)
            except:
                pass
        except Exception as e:
            await log_error(self.bot, gid, "Reaction handler error", e)

    async def translate_reaction(self, msg: discord.Message, user: discord.User):
        gid = msg.guild.id
        channels = await database.get_translation_channels(gid)
        if msg.channel.id not in channels:
            return

        text = msg.content or ""
        if not text.strip():
            return

        lang = await database.get_user_lang(user.id) or await database.get_server_lang(gid) or "en"
        lang = lang.lower()
        if lang not in SUPPORTED_LANGS:
            lang = "en"

        translated, detected = await self.translate_text(text, lang)

        embed = discord.Embed(description=translated, color=0xDE002A)
        embed.set_author(name=msg.author.display_name, icon_url=msg.author.display_avatar.url)
        embed.set_footer(text=f"Language: {lang.upper()} | Detected: {detected}")

        await user.send(embed=embed)
        self.bot.total_translations += 1

    # --------------------------------
    # Manual command
    # --------------------------------
    @app_commands.command(name="translate", description="Translate text manually.")
    async def cmd_translate(self, interaction: discord.Interaction, text: str):
        await interaction.response.defer(ephemeral=True)

        user_lang = await database.get_user_lang(interaction.user.id) or "en"

        translated, detected = await self.translate_text(text, user_lang.lower())

        embed = discord.Embed(description=translated, color=0xDE002A)
        embed.set_footer(text=f"→ {user_lang.upper()} | Detected: {detected}")
        await interaction.followup.send(embed=embed)

    # --------------------------------
    # Dropdown selection command
    # --------------------------------
    @app_commands.command(name="setmylang", description="Set personal translation language.")
    async def setlang(self, interaction: discord.Interaction):
        view = ui.View()
        view.add_item(LangSelect())
        await interaction.response.send_message(
            "Pick your preferred translation language:",
            view=view,
            ephemeral=True
        )

    # --------------------------------
    # Translation system with AI fallback
    # --------------------------------
    async def translate_text(self, text: str, lang: str):
        # Check Cache
        cached = await cache.get(text, lang)
        if cached:
            self.bot.cache_hits += 1
            return cached

        self.bot.cache_misses += 1

        # ✅ Libre Translate First
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    LIBRE_URL,
                    json={"q": text, "source": "auto", "target": lang},
                    timeout=10
                ) as r:
                    if r.status == 200:
                        data = await r.json()
                        result = (data["translatedText"], data.get("detectedLanguage", "auto"))
                        await cache.set(text, lang, result)
                        self.bot.libre_translations += 1
                        return result
        except Exception:
            pass

        # ✅ Fallback: OpenAI GPT-4o-mini Translator
        try:
            prompt = f"Translate to {SUPPORTED_LANGS[lang].split()[1][:-1]}: {text}"
            resp = CLIENT.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            output = resp.choices[0].message.content
            result = (output, "auto")

            await cache.set(text, lang, result)
            self.bot.ai_translations += 1
            return result

        except Exception as e:
            raise RuntimeError(f"Translation failed: {e}")


async def setup(bot):
    await bot.add_cog(Translate(bot))