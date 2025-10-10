# bot.py — Persistent, per-guild emoji translator with rate limits and SQLite (no addons required)
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import aiohttp
import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# fallback translator
from googletrans import Translator as GoogleTranslator
from googletrans import LANGUAGES as GOOGLE_LANGS

# ---------- Config & env ----------
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("ERROR: BOT_TOKEN environment variable is required.")
    sys.exit(1)

# Translation provider config
TRANSLATE_PROVIDER = os.getenv("TRANSLATE_PROVIDER", "libre").lower()
LIBRE_URL = os.getenv("LIBRE_URL", "https://libretranslate.com").rstrip("/")
LIBRE_KEY = os.getenv("LIBRE_KEY")  # optional

# Database config
DB_PATH = Path("data.db")

# Rate limit defaults
DEFAULT_RATE_LIMIT_COUNT = int(os.getenv("DEFAULT_RATE_LIMIT_COUNT", "5"))
DEFAULT_RATE_LIMIT_SECONDS = int(os.getenv("DEFAULT_RATE_LIMIT_SECONDS", "60"))

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("translator-bot")

# ---------- Intents & bot ----------
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.messages = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)
translator_google = GoogleTranslator()

# ---------- In-memory rate tracking ----------
rate_map: Dict[Tuple[int, int], list] = {}

# ---------- SQLite setup ----------
async def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(DB_PATH)
    await conn.execute("PRAGMA journal_mode=WAL;")
    # ✅ fixed DEFAULT placeholders
    await conn.execute(f"""
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id INTEGER PRIMARY KEY,
            channel_id INTEGER,
            emoji TEXT,
            rate_count INTEGER DEFAULT {DEFAULT_RATE_LIMIT_COUNT},
            rate_seconds INTEGER DEFAULT {DEFAULT_RATE_LIMIT_SECONDS}
        )
    """)
    await conn.commit()
    await conn.close()
    logger.info("Database initialized (SQLite).")

async def get_guild_settings(guild_id: int) -> dict:
    conn = await aiosqlite.connect(DB_PATH)
    row = await conn.execute_fetchone("SELECT channel_id, emoji, rate_count, rate_seconds FROM guild_settings WHERE guild_id = ?", (guild_id,))
    await conn.close()
    if row:
        channel_id, emoji, rate_count, rate_seconds = row
        return {
            "channel_id": channel_id,
            "emoji": emoji or "🔃",
            "rate_count": rate_count or DEFAULT_RATE_LIMIT_COUNT,
            "rate_seconds": rate_seconds or DEFAULT_RATE_LIMIT_SECONDS,
        }
    return {
        "channel_id": None,
        "emoji": "🔃",
        "rate_count": DEFAULT_RATE_LIMIT_COUNT,
        "rate_seconds": DEFAULT_RATE_LIMIT_SECONDS,
    }

async def set_guild_settings(guild_id: int, channel_id: Optional[int] = None, emoji: Optional[str] = None,
                             rate_count: Optional[int] = None, rate_seconds: Optional[int] = None):
    conn = await aiosqlite.connect(DB_PATH)
    await conn.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild_id,))
    if channel_id is not None:
        await conn.execute("UPDATE guild_settings SET channel_id = ? WHERE guild_id = ?", (channel_id, guild_id))
    if emoji is not None:
        await conn.execute("UPDATE guild_settings SET emoji = ? WHERE guild_id = ?", (emoji, guild_id))
    if rate_count is not None:
        await conn.execute("UPDATE guild_settings SET rate_count = ? WHERE guild_id = ?", (rate_count, guild_id))
    if rate_seconds is not None:
        await conn.execute("UPDATE guild_settings SET rate_seconds = ? WHERE guild_id = ?", (rate_seconds, guild_id))
    await conn.commit()
    await conn.close()
    logger.info("Updated settings for guild %s", guild_id)

# ---------- Language utilities ----------
SUPPORTED_LANGS = {code.lower() for code in GOOGLE_LANGS.keys()}

async def refresh_libre_languages():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{LIBRE_URL}/languages", timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data:
                        code = item.get("code")
                        if code:
                            SUPPORTED_LANGS.add(code.lower())
                    logger.info("Fetched LibreTranslate languages.")
    except Exception as e:
        logger.debug("Failed to refresh libre languages: %s", e)

async def is_valid_lang(code: str) -> bool:
    if not code:
        return False
    code = code.strip().lower()
    if code in SUPPORTED_LANGS:
        return True
    if TRANSLATE_PROVIDER == "libre":
        await refresh_libre_languages()
        return code in SUPPORTED_LANGS
    return False

# ---------- Translation functions ----------
async def translate_libre(text: str, dest: str, source: Optional[str] = "auto") -> Tuple[str, Optional[str]]:
    payload = {"q": text, "source": source or "auto", "target": dest, "format": "text"}
    if LIBRE_KEY:
        payload["api_key"] = LIBRE_KEY
    headers = {"Accept": "application/json"}
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{LIBRE_URL}/translate", json=payload, headers=headers, timeout=20) as resp:
            if resp.status != 200:
                txt = await resp.text()
                raise RuntimeError(f"LibreTranslate error {resp.status}: {txt}")
            data = await resp.json()
            detected = data.get("detectedLanguage") or data.get("source") or None
            return data.get("translatedText", ""), detected

async def translate_google(text: str, dest: str) -> Tuple[str, Optional[str]]:
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: translator_google.translate(text, dest=dest))
    return getattr(result, "text", str(result)), getattr(result, "src", None)

async def translate_text(text: str, dest: str) -> Tuple[str, Optional[str]]:
    if TRANSLATE_PROVIDER == "libre":
        try:
            return await translate_libre(text, dest)
        except Exception as e:
            logger.warning("LibreTranslate failed, falling back to Google: %s", e)
    return await translate_google(text, dest)

# ---------- Rate limiting ----------
def is_rate_limited(guild_id: int, user_id: int, limit_count: int, limit_seconds: int) -> bool:
    key = (guild_id, user_id)
    now = time.monotonic()
    window = [t for t in rate_map.get(key, []) if now - t <= limit_seconds]
    window.append(now)
    rate_map[key] = window
    return len(window) > limit_count

# ---------- Bot events ----------
@bot.event
async def on_ready():
    logger.info("✅ Logged in as %s", bot.user)
    await init_db()
    if TRANSLATE_PROVIDER == "libre":
        asyncio.create_task(refresh_libre_languages())
    try:
        synced = await bot.tree.sync()
        logger.info("✅ Synced %d commands", len(synced))
    except Exception as e:
        logger.exception("Sync failed: %s", e)

# ---------- Commands ----------
@bot.tree.command(name="setchannel", description="Set the translation channel (Admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def setchannel(interaction: discord.Interaction):
    guild = interaction.guild
    channels = [c for c in guild.text_channels if c.permissions_for(guild.me).send_messages]
    options = [discord.SelectOption(label=c.name, value=str(c.id)) for c in channels[:25]]
    select = discord.ui.Select(placeholder="Select a translation channel", options=options)

    async def callback(inner: discord.Interaction):
        cid = int(select.values[0])
        await set_guild_settings(guild.id, channel_id=cid)
        await inner.response.send_message(f"✅ Translation channel set to <#{cid}>", ephemeral=True)

    select.callback = callback
    view = discord.ui.View()
    view.add_item(select)
    await interaction.response.send_message("Select a channel:", view=view, ephemeral=True)

@bot.tree.command(name="setemoji", description="Set the reaction emoji (Admin only)")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(emoji="Emoji to use for translations")
async def setemoji(interaction: discord.Interaction, emoji: str):
    guild = interaction.guild
    await set_guild_settings(guild.id, emoji=emoji)
    await interaction.response.send_message(f"✅ Emoji set to `{emoji}`", ephemeral=True)

@bot.tree.command(name="setratelimit", description="Set rate limit (Admin only)")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(count="Max translations", seconds="Per seconds")
async def setratelimit(interaction: discord.Interaction, count: int, seconds: int):
    guild = interaction.guild
    await set_guild_settings(guild.id, rate_count=count, rate_seconds=seconds)
    await interaction.response.send_message(f"✅ Limit: {count} translations per {seconds}s", ephemeral=True)

@bot.tree.command(name="translate", description="Translate text manually")
@app_commands.describe(text="Text to translate", target="Language code (e.g. en, fr)")
async def slash_translate(interaction: discord.Interaction, text: str, target: str):
    await interaction.response.defer(ephemeral=True)
    if not await is_valid_lang(target):
        await interaction.followup.send("❌ Invalid language code.", ephemeral=True)
        return
    try:
        translated, detected = await translate_text(text, target)
        msg = f"**({target})** {translated}"
        if detected:
            msg = f"Detected: `{detected}`\n" + msg
        await interaction.followup.send(msg, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Translation failed: {e}", ephemeral=True)

# ---------- Message reaction flow ----------
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return
    settings = await get_guild_settings(message.guild.id)
    if settings["channel_id"] == message.channel.id:
        try:
            await message.add_reaction(settings["emoji"])
        except Exception:
            pass
    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or not reaction.message.guild:
        return
    settings = await get_guild_settings(reaction.message.guild.id)
    if str(reaction.emoji) != settings["emoji"]:
        return
    if reaction.message.channel.id != settings["channel_id"]:
        return

    limit_count = settings["rate_count"]
    limit_seconds = settings["rate_seconds"]
    if is_rate_limited(reaction.message.guild.id, user.id, limit_count, limit_seconds):
        try:
            await user.send(f"🚫 Rate limit: {limit_count}/{limit_seconds}s.")
        except Exception:
            pass
        try:
            await reaction.remove(user)
        except Exception:
            pass
        return

    try:
        await reaction.remove(user)
    except Exception:
        pass

    content = reaction.message.content
    if not content:
        await user.send("⚠️ No text found in that message.")
        return

    await user.send("🌐 Reply with a language code (e.g., en, fr):")

    def check(m):
        return m.author == user and isinstance(m.channel, discord.DMChannel)

    try:
        reply = await bot.wait_for("message", check=check, timeout=60)
    except asyncio.TimeoutError:
        await user.send("⌛ Timed out. React again to retry.")
        return

    lang = reply.content.strip().lower()
    if not await is_valid_lang(lang):
        await user.send("❌ Invalid language code.")
        return

    try:
        translated, detected = await translate_text(content, lang)
        msg = f"✅ **Translated ({lang})**\n"
        if detected:
            msg += f"Detected source: `{detected}`\n\n"
        msg += translated
        for chunk in [msg[i:i+1900] for i in range(0, len(msg), 1900)]:
            await user.send(chunk)
    except Exception as e:
        await user.send(f"❌ Error: {e}")

# ---------- Run ----------
def run():
    try:
        asyncio.run(init_db())
        bot.run(TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot stopped.")

if __name__ == "__main__":
    run()
