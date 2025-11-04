# cogs/translate.py (only showing full for safety)
import os
import re
import asyncio
import aiohttp
import discord
from discord.ext import commands

from utils.cache import TranslationCache
from utils import database
from utils.logging_utils import log_error

BOT_COLOR = 0xDE002A
LIBRE_URL = os.getenv("LIBRE_URL", "https://libretranslate.de/translate")
CACHE_TTL = 60 * 60 * 24
AI_COST_CAP_EUR = 10.0
AI_WARN_AT_EUR = 8.0
SUPPORTED_LANGS = ["en","de","es","fr","it","ja","ko","zh"]

SLANG_WORDS = {
    "cap","no cap","bet","sus","lowkey","highkey","sigma","rizz","gyatt","gyat","sheesh",
    "skibidi","fanum","ohio","mid","copium","ratio","cope","based","cringe","drip","npc",
    "goat","fax","ate","smash","bussin","yeet","fire","lit","pog","poggers","kekw","xdd",
    "bruh","lmao","lol","fr","ong",
}
EMOJI_REGEX = re.compile(r"[\U0001F1E6-\U0001F1FF\U0001F300-\U0001F6FF\U0001F900-\U0001FAFF\U00002700-\U000027BF]")
CUSTOM_EMOJI_RE = re.compile(r"^<(a?):([a-zA-Z0-9_]+):(\d+)>$")

from openai import OpenAI
_oai_client = None
def get_oai_client():
    global _oai_client
    if _oai_client is None:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            return None
        try:
            _oai_client = OpenAI(api_key=key)
        except Exception:
            _oai_client = None
    return _oai_client

cache = TranslationCache(ttl=CACHE_TTL)

def needs_ai(text: str) -> bool:
    t = text.lower()
    if len(t) > 200: return True
    if EMOJI_REGEX.search(t): return True
    for w in SLANG_WORDS:
        if re.search(rf"\b{re.escape(w)}\b", t): return True
    return False

def parse_custom_emoji(s: str):
    m = CUSTOM_EMOJI_RE.match(s or "")
    if not m: return None
    animated_flag, name, eid = m.groups()
    return (bool(animated_flag), name, int(eid))

def emoji_matches(config_emote: str, reacted_emoji) -> bool:
    """Accept exact match; if config is custom, also accept fallback 🔁."""
    # Fallback acceptance
    if str(reacted_emoji) == "🔁":
        return True if CUSTOM_EMOJI_RE.match(config_emote or "") else (config_emote == "🔁")
    # Unicode configured
    if not CUSTOM_EMOJI_RE.match(config_emote or ""):
        return str(reacted_emoji) == (config_emote or "🔁")
    # Custom by ID
    parsed = parse_custom_emoji(config_emote)
    if not parsed: return False
    _, _, cfg_id = parsed
    try:
        return int(getattr(reacted_emoji, "id", 0) or 0) == cfg_id
    except Exception:
        return False

async def libre_translate(text: str, target_lang: str) -> str | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                LIBRE_URL,
                json={"q": text, "source": "auto", "target": target_lang, "format": "text"},
                headers={"Content-Type": "application/json"},
                timeout=12,
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data.get("translatedText") or None
    except Exception:
        return None

async def openai_translate(text: str, target_lang: str):
    client = get_oai_client()
    if not client:
        return None, 0, 0.0

    def _call():
        return client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system",
                 "content": f"Translate the user's message to '{target_lang}'. Preserve tone, slang & emojis. Return only the translation."},
                {"role": "user", "content": text},
            ],
            temperature=0.2,
        )

    try:
        resp = await asyncio.to_thread(_call)
        out = resp.choices[0].message.content.strip()
        tokens = (resp.usage.total_tokens if resp.usage and resp.usage.total_tokens else 0)
        est_eur = tokens * 0.0000006
        await database.add_ai_usage(tokens, est_eur)
        return out, tokens, est_eur
    except Exception:
        return None, 0, 0.0

class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._inflight = set()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        gid = message.guild.id
        allowed = await database.get_translation_channels(gid)
        if not allowed or message.channel.id not in allowed:
            return

        emote = (await database.get_bot_emote(gid)) or "🔁"

        # Try configured emote
        try:
            await message.add_reaction(emote)
            return
        except Exception:
            pass

        # Try custom by ID
        parsed = parse_custom_emoji(emote)
        if parsed:
            _, name, eid = parsed
            try:
                await message.add_reaction(discord.PartialEmoji(name=name, id=eid))
                return
            except Exception as e:
                await log_error(self.bot, gid, f"Could not add custom emote {emote} in #{message.channel.id}", e)

        # Fallback to 🔁 if custom invalid or add failed
        try:
            await message.add_reaction("🔁")
        except Exception as e:
            await log_error(self.bot, gid, f"Could not add reaction emote '{emote}' in #{message.channel.id}", e)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user.bot or not reaction.message.guild:
            return

        guild = reaction.message.guild
        gid = guild.id
        allowed = await database.get_translation_channels(gid)
        if not allowed or reaction.message.channel.id not in allowed:
            return

        config_emote = (await database.get_bot_emote(gid)) or "🔁"
        if not emoji_matches(config_emote, reaction.emoji):
            return

        key = (reaction.message.id, user.id)
        if key in self._inflight:
            return
        self._inflight.add(key)

        try:
            target = await database.get_user_lang(user.id) or await database.get_server_lang(gid) or "en"
            if target not in SUPPORTED_LANGS:
                target = "en"
            await self._translate_and_send(reaction, user, target)
        except Exception as e:
            await log_error(self.bot, gid, "Reaction handler error", e, admin_notify=True)
        finally:
            await asyncio.sleep(0.5)
            self._inflight.discard(key)

    async def _translate_and_send(self, reaction: discord.Reaction, user: discord.User, target_lang: str):
        msg = reaction.message
        original = msg.content or ""
        if not original.strip():
            return

        # Cache
        cached = await cache.get(original, target_lang)
        if cached:
            translated = cached
            self.bot.cached_translations += 1
            self.bot.cache_hits += 1
        else:
            self.bot.cache_misses += 1
            ai_enabled = await database.get_ai_enabled(msg.guild.id)
            force_ai = needs_ai(original)
            translated = None
            used_ai = False

            if ai_enabled and force_ai:
                translated, _, _ = await openai_translate(original, target_lang)
                used_ai = translated is not None

            if translated is None:
                translated = await libre_translate(original, target_lang)
                if translated:
                    self.bot.libre_translations += 1

            if translated is None and ai_enabled:
                translated, _, _ = await openai_translate(original, target_lang)
                used_ai = translated is not None

            if translated is None:
                await log_error(self.bot, msg.guild.id, "Translation failed for a message (both engines).")
                return

            if used_ai:
                self.bot.ai_translations += 1
                _, eur = await database.get_current_ai_usage()
                if eur >= AI_COST_CAP_EUR:
                    await database.set_ai_enabled(msg.guild.id, False)
                    ch_id = await database.get_error_channel(msg.guild.id)
                    if ch_id and (ch := msg.guild.get_channel(ch_id)):
                        await ch.send("🔴 AI disabled — monthly cap reached. Using Libre only.")
                elif eur >= AI_WARN_AT_EUR:
                    ch_id = await database.get_error_channel(msg.guild.id)
                    if ch_id and (ch := msg.guild.get_channel(ch_id)):
                        await ch.send(f"⚠️ AI usage **€{eur:.2f}/€{AI_COST_CAP_EUR:.2f}**. Switching to Libre soon.")

            await cache.set(original, target_lang, translated)

        embed = discord.Embed(description=translated, color=BOT_COLOR)
        embed.set_author(name=msg.author.display_name, icon_url=msg.author.display_avatar.url)
        embed.set_footer(text=f"{msg.created_at.strftime('%H:%M UTC')} • → {target_lang}")
        embed.description += f"\n[View original]({msg.jump_url})"

        try:
            await user.send(embed=embed)
        except Exception as e:
            await log_error(self.bot, msg.guild.id, f"DM to user {user.id} failed; replying in channel.", e)
            try:
                await msg.reply(embed=embed, mention_author=False)
            except Exception as e2:
                await log_error(self.bot, msg.guild.id, "Channel reply failed after DM fail.", e2)

        try:
            await reaction.remove(user)
        except Exception:
            pass

        self.bot.total_translations = getattr(self.bot, "total_translations", 0) + 1


async def setup(bot):
    await bot.add_cog(Translate(bot))