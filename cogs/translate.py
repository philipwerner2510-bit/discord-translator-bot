import os
import re
import asyncio
import aiohttp
import discord
from discord.ext import commands

from utils.cache import TranslationCache
from utils import database
from utils.logging_utils import log_error

# ---------- CONFIG ----------
BOT_COLOR = 0xDE002A
LIBRE_URL = os.getenv("LIBRE_URL", "https://libretranslate.de/translate")
CACHE_TTL = 60 * 60 * 24  # 24h
AI_COST_CAP_EUR = 10.0
AI_WARN_AT_EUR = 8.0
SUPPORTED_LANGS = ["en", "de", "es", "fr", "it", "ja", "ko", "zh"]

# slang/emoji detection (aggressive)
SLANG_WORDS = {
    "cap","no cap","bet","sus","lowkey","highkey","sigma","rizz","gyatt",
    "gyat","sheesh","skibidi","fanum","ohio","mid","copium","ratio","cope",
    "based","cringe","drip","npc","goat","fax","ate","smash","bussin","yeet",
    "fire","lit","pog","poggers","kekw","xdd","bruh","lmao","lol","fr","ong",
}
EMOJI_REGEX = re.compile(
    r"[\U0001F1E6-\U0001F1FF\U0001F300-\U0001F6FF\U0001F900-\U0001FAFF\U00002700-\U000027BF]"
)

CUSTOM_EMOJI_RE = re.compile(r"^<(a?):([a-zA-Z0-9_]+):(\d+)>$")

# ---------- OpenAI (lazy init) ----------
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

# ---------- Cache ----------
cache = TranslationCache(ttl=CACHE_TTL)

# ---------- Heuristics ----------
def needs_ai(text: str) -> bool:
    t = text.lower()
    if len(t) > 200:
        return True
    if EMOJI_REGEX.search(t):
        return True
    for w in SLANG_WORDS:
        if re.search(rf"\b{re.escape(w)}\b", t):
            return True
    return False

# ---------- Emoji helpers ----------
def parse_custom_emoji(s: str):
    """
    Returns (animated: bool, name: str, id: int) if s is <a:name:id> or <name:id>, else None
    """
    m = CUSTOM_EMOJI_RE.match(s or "")
    if not m:
        return None
    animated_flag, name, eid = m.groups()
    return (bool(animated_flag), name, int(eid))

def emoji_matches(config_emote: str, reacted_emoji) -> bool:
    """
    Compare configured emote string vs the actual reacted emoji (Unicode or custom).
    """
    # Unicode case
    if not CUSTOM_EMOJI_RE.match(config_emote or ""):
        return str(reacted_emoji) == (config_emote or "🔁")

    # Custom: compare by ID if possible
    parsed = parse_custom_emoji(config_emote)
    if not parsed:
        return False
    _, _, cfg_id = parsed

    # discord.PartialEmoji or Emoji -> has .id
    try:
        return int(getattr(reacted_emoji, "id", 0) or 0) == cfg_id
    except Exception:
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
    client = get_oai_client()
    if not client:
        return None, 0, 0.0

    def _call():
        return client.chat.completions.create(
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
        est_eur = tokens * 0.0000006  # rough safe estimate
        await database.add_ai_usage(tokens, est_eur)
        return out, tokens, est_eur
    except Exception:
        return None, 0, 0.0

# ---------- Cog ----------
class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._inflight = set()  # (message_id, user_id)

    # -----------------------
    # Auto-react on new messages in selected channels
    # -----------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        gid = message.guild.id
        allowed = await database.get_translation_channels(gid)
        if not allowed or message.channel.id not in allowed:
            return

        emote = (await database.get_bot_emote(gid)) or "🔁"
        # Try Unicode first
        try:
            await message.add_reaction(emote)
            return
        except Exception:
            pass

        # Try custom emoji if configured like <a:name:id>
        parsed = parse_custom_emoji(emote)
        if parsed:
            _, name, eid = parsed
            try:
                partial = discord.PartialEmoji(name=name, id=eid)
                await message.add_reaction(partial)
                return
            except Exception as e:
                await log_error(self.bot, gid, f"Could not add custom emote {emote} in #{message.channel.id}", e)

        # Log if neither worked
        await log_error(self.bot, gid, f"Could not add reaction emote '{emote}' in #{message.channel.id}")

    # -----------------------
    # React-to-translate
    # -----------------------
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user.bot or not reaction.message.guild:
            return

        guild = reaction.message.guild
        gid = guild.id

        # channel gate
        allowed = await database.get_translation_channels(gid)
        if not allowed or reaction.message.channel.id not in allowed:
            return

        # emote gate
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

        # 1) Cache
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

            # AI first if it obviously needs it
            if ai_enabled and force_ai:
                translated, _, _ = await openai_translate(original, target_lang)
                used_ai = translated is not None

            # Libre (primary path)
            if translated is None:
                translated = await libre_translate(original, target_lang)
                if translated:
                    self.bot.libre_translations += 1

            # AI fallback if Libre failed and AI enabled
            if translated is None and ai_enabled:
                translated, _, _ = await openai_translate(original, target_lang)
                used_ai = translated is not None

            if translated is None:
                await log_error(self.bot, msg.guild.id, "Translation failed for a message (both engines).")
                return

            if used_ai:
                self.bot.ai_translations += 1
                # Cap notifications
                _, eur = await database.get_current_ai_usage()
                if eur >= AI_COST_CAP_EUR:
                    await database.set_ai_enabled(msg.guild.id, False)
                    ch_id = await database.get_error_channel(msg.guild.id)
                    if ch_id and (ch := msg.guild.get_channel(ch_id)):
                        await ch.send("🔴 AI disabled — monthly cap reached. Using Libre only.")
                elif eur >= AI_WARN_AT_EUR:
                    ch_id = await database.get_error_channel(msg.guild.id)
                    if ch_id and (ch := msg.guild.get_channel(ch_id)):
                        await ch.send(f"⚠️ AI usage **€{eur:.2f}/€{AI_COST_CAP_EUR:.2f}**. "
                                      f"Bot will switch to Libre-only soon.")

            # Save to cache
            await cache.set(original, target_lang, translated)

        # Build embed
        embed = discord.Embed(description=translated, color=BOT_COLOR)
        embed.set_author(name=msg.author.display_name, icon_url=msg.author.display_avatar.url)
        ts = msg.created_at.strftime("%H:%M UTC")
        embed.set_footer(text=f"{ts} • → {target_lang}")
        embed.description += f"\n[View original]({msg.jump_url})"

        # Try DM first; if closed, reply in channel
        try:
            await user.send(embed=embed)
        except Exception as e:
            # Let admin know if DMs are closed
            await log_error(self.bot, msg.guild.id, f"DM to user {user.id} failed; replying in channel.", e)
            try:
                await msg.reply(embed=embed, mention_author=False)
            except Exception as e2:
                await log_error(self.bot, msg.guild.id, "Channel reply failed after DM fail.", e2)

        # Remove the user reaction to show completion
        try:
            await reaction.remove(user)
        except Exception:
            pass

        self.bot.total_translations = getattr(self.bot, "total_translations", 0) + 1


async def setup(bot):
    await bot.add_cog(Translate(bot))