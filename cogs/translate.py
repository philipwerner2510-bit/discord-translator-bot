import os
import re
import asyncio
from datetime import datetime
import aiohttp
import discord
from discord.ext import commands

from utils.cache import TranslationCache
from utils import database
from utils.logging_utils import log_error

# ---------- CONFIG ----------
BOT_COLOR = 0xde002a
LIBRE_URL = os.getenv("LIBRE_URL", "https://libretranslate.de/translate")  # public for now
CACHE_TTL = 60 * 60 * 24  # 24h
AI_COST_CAP_EUR = 10.0
AI_WARN_AT_EUR = 8.0
SUPPORTED_LANGS = ["en","de","es","fr","it","ja","ko","zh"]

# Aggressive slang/emoji detector (you chose “A”)
SLANG_WORDS = {
    "cap","no cap","bet","sus","lowkey","highkey","sigma","rizz","gyatt",
    "gyat","sheesh","skibidi","fanum","ohio","mid","copium","ratio","cope",
    "based","cringe","drip","npc","goat","fax","ate","smash","bussin","yeet",
    "fire","lit","pog","poggers","kekw","xdd","bruh","lmao","lol","fr","ong",
}
EMOJI_REGEX = re.compile(
    r"[\U0001F1E6-\U0001F1FF\U0001F300-\U0001F6FF\U0001F900-\U0001FAFF\U00002700-\U000027BF]"
)

# OpenAI (sync client; we’ll call it via asyncio.to_thread)
from openai import OpenAI
_oai_key = os.getenv("OPENAI_API_KEY")
_oai_client = OpenAI(api_key=_oai_key) if _oai_key else None

# Shared cache
cache = TranslationCache(ttl=CACHE_TTL)


# ---------- Heuristics ----------
def needs_ai(text: str) -> bool:
    t = text.lower()
    if len(t) > 200:
        return True
    if EMOJI_REGEX.search(t):
        return True
    # if any slang word appears as a standalone token
    for w in SLANG_WORDS:
        if re.search(rf"\b{re.escape(w)}\b", t):
            return True
    return False


# ---------- Engines ----------
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


async def openai_translate(text: str, target_lang: str) -> tuple[str | None, int, float]:
    """Return (translation, tokens, estimated_eur). Uses GPT-4o mini."""
    if not _oai_client:
        return None, 0, 0.0

    def _call():
        return _oai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system",
                 "content": f"You are a high-quality translator. Translate the user's message to '{target_lang}'. "
                            f"Preserve tone, slang and emojis. Return only the translation."},
                {"role": "user", "content": text},
            ],
            temperature=0.2,
        )

    try:
        resp = await asyncio.to_thread(_call)
        out = resp.choices[0].message.content.strip()
        tokens = (resp.usage.total_tokens if resp.usage and resp.usage.total_tokens else 0)
        # simple rough EUR estimate: ~$0.0000006/token → €0.0000006 approx (kept tiny and safe)
        est_eur = tokens * 0.0000006
        await database.add_ai_usage(tokens, est_eur)
        return out, tokens, est_eur
    except Exception:
        return None, 0, 0.0


# ---------- Cog ----------
class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._inflight = set()  # (message_id, user_id)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Auto-react in configured channels with the bot's emote (if your other cog does this, you can skip)
        # Kept minimal here—your Admin cog handles emote + channels.
        pass

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user.bot or not reaction.message.guild:
            return

        guild = reaction.message.guild
        allowed = await database.get_translation_channels(guild.id)
        if not allowed or reaction.message.channel.id not in allowed:
            return

        key = (reaction.message.id, user.id)
        if key in self._inflight:
            return
        self._inflight.add(key)

        try:
            # personal target language or server default
            target = await database.get_user_lang(user.id) or await database.get_server_lang(guild.id) or "en"
            if target not in SUPPORTED_LANGS:
                target = "en"

            await self._translate_and_send(reaction, user, target)
        except Exception as e:
            await log_error(self.bot, guild.id, "Reaction handler error", e, admin_notify=True)
        finally:
            # let Discord settle before allowing another translate on same key
            await asyncio.sleep(1.0)
            self._inflight.discard(key)

    async def _translate_and_send(self, reaction: discord.Reaction, user: discord.User, target_lang: str):
        msg = reaction.message
        original = msg.content or ""
        if not original.strip():
            return

        # 1) Cache
        cached = await cache.get(original, target_lang)
        if cached:
            translated = cached
        else:
            # 2) Decide engine
            ai_enabled = await database.get_ai_enabled(msg.guild.id)
            force_ai = needs_ai(original)

            translated = None
            used_ai = False

            if ai_enabled and force_ai:
                translated, _, _ = await openai_translate(original, target_lang)
                used_ai = translated is not None

            # 3) Libre first if not already translated by AI
            if translated is None:
                translated = await libre_translate(original, target_lang)

            # 4) AI fallback if Libre failed and AI allowed
            if translated is None and ai_enabled:
                translated, _, _ = await openai_translate(original, target_lang)
                used_ai = translated is not None

            if translated is None:
                # give up silently to avoid spam
                return

            # Save to cache
            await cache.set(original, target_lang, translated)

            # Warn/admin notify if cost approaching cap
            if used_ai:
                _, eur = await database.get_current_ai_usage()
                if eur >= AI_COST_CAP_EUR:
                    await database.set_ai_enabled(msg.guild.id, False)
                    ch_id = await database.get_error_channel(msg.guild.id)
                    if ch_id and (ch := msg.guild.get_channel(ch_id)):
                        await ch.send("🔴 AI translation disabled — monthly cap reached. Falling back to Libre only.")
                elif eur >= AI_WARN_AT_EUR:
                    ch_id = await database.get_error_channel(msg.guild.id)
                    if ch_id and (ch := msg.guild.get_channel(ch_id)):
                        await ch.send(f"⚠️ AI usage is at **€{eur:.2f}/€{AI_COST_CAP_EUR:.2f}**. "
                                      f"Bot will switch to Libre-only soon.")

        # Build a clean embed reply
        embed = discord.Embed(description=translated, color=BOT_COLOR)
        embed.set_author(name=msg.author.display_name, icon_url=msg.author.display_avatar.url)
        ts = msg.created_at.strftime("%H:%M UTC")
        embed.set_footer(text=f"{ts} • → {target_lang}")
        embed.description += f"\n[View original]({msg.jump_url})"

        # Try DM first (your original UX), else reply in channel silently
        try:
            await user.send(embed=embed)
        except Exception:
            await msg.reply(embed=embed, mention_author=False)

        # Try remove the user's reaction to show it was handled
        try:
            await reaction.remove(user)
        except Exception:
            pass

        # Count
        self.bot.total_translations = getattr(self.bot, "total_translations", 0) + 1


async def setup(bot):
    await bot.add_cog(Translate(bot))