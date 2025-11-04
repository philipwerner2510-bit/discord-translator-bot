import re
import aiohttp
import asyncio
import discord
from datetime import datetime
from discord.ext import commands
from googletrans import Translator as GoogleTranslator

from utils import database
from utils.config import SUPPORTED_LANGS, CONFIG
from utils.cache import TranslationCache
from utils.logging_utils import log_error

LIBRE_URL = "https://libretranslate.de/translate"
CACHE_TTL = 300
cache = TranslationCache(ttl=CACHE_TTL)

CUSTOM_EMOJI_RE = re.compile(r"<(a?):([a-zA-Z0-9_]+):(\d+)>")

class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.google_translator = GoogleTranslator()
        self.pending_choice = {}
        self.processing = set()

    # ------------------------------------------------
    # Manual translation
    # ------------------------------------------------
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        gid = message.guild.id
        allowed = await database.get_translation_channels(gid)
        if not allowed or message.channel.id not in allowed:
            return

        emote = await database.get_bot_emote(gid) or "🔃"
        try:
            await message.add_reaction(emote)
        except Exception:
            m = CUSTOM_EMOJI_RE.match(emote)
            if m:
                a, name, eid = m.groups()
                try:
                    await message.add_reaction(
                        discord.PartialEmoji(name=name, animated=bool(a), id=int(eid))
                    )
                except Exception:
                    pass

    # ------------------------------------------------
    # Reaction triggers language picker
    # ------------------------------------------------
    async def on_reaction_add(self, reaction, user):
        if user.bot or not reaction.message.guild:
            return

        message = reaction.message
        gid = message.guild.id

        allowed = await database.get_translation_channels(gid)
        if not allowed or message.channel.id not in allowed:
            return

        conf_emote = await database.get_bot_emote(gid) or "🔃"
        if str(reaction.emoji) != conf_emote:
            return

        key = (message.id, user.id)
        if key in self.processing:
            return
        self.processing.add(key)

        await self.ask_language(reaction, user)

    # ------------------------------------------------
    # Show select menu for user translation language
    # ------------------------------------------------
    async def ask_language(self, reaction, user):
        msg = reaction.message
        guild = msg.guild
        gid = guild.id

        default = await database.get_user_lang(user.id)
        placeholder = f"Select language (default: {default or 'server default'})"

        select = discord.ui.Select(
            placeholder=placeholder,
            min_values=1, max_values=1,
            options=[
                discord.SelectOption(label=code.upper(), value=code)
                for code in SUPPORTED_LANGS[:25]
            ]
        )

        async def lang_chosen(inter):
            lang = select.values[0]
            await self.process_translation(msg, user, lang)
            await inter.response.edit_message(content=f"✅ Translating to `{lang}`…", view=None)

        select.callback = lang_chosen
        view = discord.ui.View(timeout=60)
        view.add_item(select)

        try:
            await user.send(
                f"🌍 Choose translation for: **{msg.content[:50]}…**",
                view=view
            )
        except:
            await log_error(self.bot, gid,
                            f"DM blocked for user {user.id}",
                            admin_notify=True)
        finally:
            try:
                await reaction.remove(user)
            except:
                pass

    # ------------------------------------------------
    # Translation core logic
    # ------------------------------------------------
    async def process_translation(self, message, user, target):
        gid = message.guild.id
        text = message.content or ""

        try:
            translated, src = await self.translate_text(text, target)

            embed = discord.Embed(description=translated, color=0xDE002A)
            embed.set_author(
                name=message.author.display_name,
                icon_url=message.author.display_avatar.url
            )
            timestamp = message.created_at.strftime("%H:%M UTC")
            embed.set_footer(
                text=f"{timestamp} | to: {target} | detected: {src}"
            )
            embed.description += (
                f"\n[Original]("
                f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id})"
            )

            await user.send(embed=embed)

            self.bot.total_translations += 1
            await database.increment_user_counter(user.id, 1)
            await database.increment_guild_counter(gid, 1)

        except Exception as e:
            await log_error(self.bot, gid, "Translation failed", e, admin_notify=True)
        finally:
            key = (message.id, user.id)
            self.processing.discard(key)

    # ------------------------------------------------
    # Translate helper (cache → Libre → Google)
    # ------------------------------------------------
    async def translate_text(self, text: str, target: str):
        if target not in SUPPORTED_LANGS:
            raise ValueError("Unsupported language")

        cached = await cache.get(text, target)
        if cached:
            return cached

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    LIBRE_URL,
                    json={"q": text, "source": "auto", "target": target},
                    headers={"Content-Type": "application/json"},
                    timeout=10
                ) as r:
                    if r.status == 200:
                        data = await r.json()
                        result = (data.get("translatedText", ""), data.get("detectedLanguage", "unknown"))
                        await cache.set(text, target, result)
                        return result
        except:
            pass

        result = self.google_translator.translate(text, dest=target)
        out = (result.text, result.src)
        await cache.set(text, target, out)
        return out

async def setup(bot):
    await bot.add_cog(Translate(bot))