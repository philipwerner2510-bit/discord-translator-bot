# cogs/translate.py
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
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

CACHE_TTL = 60 * 60 * 24
AI_COST_CAP_EUR = 10.0
AI_WARN_AT_EUR = 8.0

# Big language catalog (50+). Any of these are accepted inputs.
LANG_CATALOG = [
    ("en","🇬🇧","English"), ("de","🇩🇪","German"), ("fr","🇫🇷","French"), ("es","🇪🇸","Spanish"),
    ("it","🇮🇹","Italian"), ("pt","🇵🇹","Portuguese"), ("ru","🇷🇺","Russian"), ("zh","🇨🇳","Chinese"),
    ("ja","🇯🇵","Japanese"), ("ko","🇰🇷","Korean"), ("ar","🇸🇦","Arabic"), ("tr","🇹🇷","Turkish"),
    ("nl","🇳🇱","Dutch"), ("sv","🇸🇪","Swedish"), ("no","🇳🇴","Norwegian"), ("da","🇩🇰","Danish"),
    ("fi","🇫🇮","Finnish"), ("pl","🇵🇱","Polish"), ("cs","🇨🇿","Czech"), ("sk","🇸🇰","Slovak"),
    ("hu","🇭🇺","Hungarian"), ("ro","🇷🇴","Romanian"), ("bg","🇧🇬","Bulgarian"), ("el","🇬🇷","Greek"),
    ("uk","🇺🇦","Ukrainian"), ("he","🇮🇱","Hebrew"), ("hi","🇮🇳","Hindi"), ("bn","🇧🇩","Bengali"),
    ("ta","🇮🇳","Tamil"), ("te","🇮🇳","Telugu"), ("mr","🇮🇳","Marathi"), ("gu","🇮🇳","Gujarati"),
    ("pa","🇮🇳","Punjabi"), ("ur","🇵🇰","Urdu"), ("vi","🇻🇳","Vietnamese"), ("th","🇹🇭","Thai"),
    ("id","🇮🇩","Indonesian"), ("ms","🇲🇾","Malay"), ("fa","🇮🇷","Persian"), ("sw","🇰🇪","Swahili"),
    ("am","🇪🇹","Amharic"), ("yo","🇳🇬","Yoruba"), ("ha","🇳🇬","Hausa"), ("az","🇦🇿","Azerbaijani"),
    ("ka","🇬🇪","Georgian"), ("et","🇪🇪","Estonian"), ("lv","🇱🇻","Latvian"), ("lt","🇱🇹","Lithuanian"),
    ("sr","🇷🇸","Serbian"), ("hr","🇭🇷","Croatian"), ("sl","🇸🇮","Slovenian"), ("ga","🇮🇪","Irish"),
    ("is","🇮🇸","Icelandic"), ("mt","🇲🇹","Maltese"), ("af","🇿🇦","Afrikaans"), ("zu","🇿🇦","Zulu"),
    ("xh","🇿🇦","Xhosa"), ("fil","🇵🇭","Filipino"),
]
SUPPORTED_LANGS = {code for code,_,_ in LANG_CATALOG}

# Libre works best for this subset; everything else will prefer AI.
LIBRE_GOOD = {"en","de","fr","es","it","pt","ru","zh","ja","ko","tr","nl","sv","no","da","fi","pl","cs","el","uk","ro","bg","he","ar","vi","th","id","ms"}

# Slang/emoji heuristic
SLANG_WORDS = {
    "cap","no cap","bet","sus","lowkey","highkey","sigma","rizz","gyatt","gyat","sheesh",
    "skibidi","fanum","ohio","mid","copium","ratio","cope","based","cringe","drip","npc",
    "goat","fax","ate","smash","bussin","yeet","fire","lit","pog","poggers","kekw","xdd",
    "bruh","lmao","lol","fr","ong",
}
EMOJI_REGEX = re.compile(r"[\U0001F1E6-\U0001F1FF\U0001F300-\U0001F6FF\U0001F900-\U0001FAFF\U00002700-\U000027BF]")
CUSTOM_EMOJI_RE = re.compile(r"^<(a?):([a-zA-Z0-9_]+):(\d+)>$")

# OpenAI (lazy)
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
    # Always accept 🔁 as a safe fallback trigger
    if str(reacted_emoji) == "🔁":
        return True if CUSTOM_EMOJI_RE.match(config_emote or "") else (config_emote == "🔁")
    if not CUSTOM_EMOJI_RE.match(config_emote or ""):
        return str(reacted_emoji) == (config_emote or "🔁")
    parsed = parse_custom_emoji(config_emote)
    if not parsed: return False
    _, _, cfg_id = parsed
    try:
        return int(getattr(reacted_emoji, "id", 0) or 0) == cfg_id
    except Exception:
        return False

async def libre_translate(text: str, target_lang: str) -> tuple[str | None, str]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                LIBRE_URL,
                json={"q": text, "source": "auto", "target": target_lang, "format": "text"},
                headers={"Content-Type": "application/json"},
                timeout=12,
            ) as resp:
                if resp.status != 200:
                    return None, f"http_{resp.status}"
                data = await resp.json()
                return (data.get("translatedText") or None), "ok"
    except Exception as e:
        return None, f"exception:{type(e).__name__}"

async def openai_translate(text: str, target_lang: str) -> tuple[str | None, int, float, str]:
    client = get_oai_client()
    if not client:
        return None, 0, 0.0, "no_client"

    def _call():
        return client.chat.completions.create(
            model=OPENAI_MODEL,
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
        return out, tokens, est_eur, "ok"
    except Exception as e:
        return None, 0, 0.0, f"exception:{type(e).__name__}"

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
            libre_reason = "skipped"
            ai_reason = "skipped"

            # Strategy:
            # - If language is in LIBRE_GOOD and not clearly slangy → try Libre first
            # - Else prefer AI (if enabled), then fall back to Libre
            prefer_libre = (target_lang in LIBRE_GOOD) and not force_ai

            if prefer_libre:
                translated, libre_reason = await libre_translate(original, target_lang)
                if translated:
                    self.bot.libre_translations += 1
                elif ai_enabled:
                    translated, _, _, ai_reason = await openai_translate(original, target_lang)
                    used_ai = translated is not None
            else:
                if ai_enabled:
                    translated, _, _, ai_reason = await openai_translate(original, target_lang)
                    used_ai = translated is not None
                if translated is None:
                    translated, libre_reason = await libre_translate(original, target_lang)
                    if translated:
                        self.bot.libre_translations += 1

            if translated is None:
                await log_error(
                    self.bot, msg.guild.id,
                    f"Translation failed. libre={libre_reason} ai={ai_reason} (enabled={ai_enabled})"
                )
                notice = (
                    "⚠️ I couldn't translate this right now.\n"
                    f"• Libre: **{libre_reason}**\n"
                    f"• AI: **{ai_reason}**\n\n"
                    "Admins can run **/librestatus** and **/settings → 🧪 Test AI Now**.\n"
                    "Use **/aisettings true** to enable AI fallback if disabled."
                )
                try:
                    await user.send(notice)
                except Exception:
                    try:
                        await msg.reply(notice, mention_author=False)
                    except Exception:
                        pass
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