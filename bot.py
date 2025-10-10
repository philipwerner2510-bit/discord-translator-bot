# bot.py — Persistent, per-guild emoji translator with rate limits and SQLite (fallback to Postgres)
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

# Database config: if DATABASE_URL is set and starts with postgres, you can wire PostgreSQL later.
DATABASE_URL = os.getenv("DATABASE_URL")  # e.g. postgresql://user:pass@host/dbname
DB_PATH = Path("data.db")

# Rate limit defaults (per-guild, can be changed by /setratelimit)
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
# key: (guild_id, user_id) -> list of timestamps
rate_map: Dict[Tuple[int, int], list] = {}

# ---------- Utilities: DB wrapper for SQLite (simple) ----------
# We'll use aiosqlite for portability (no addons required). If DATABASE_URL is set for Postgres,
# the code can be extended — for now we fallback to SQLite stored in data.db.
async def init_db():
    # ensure folder exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(DB_PATH)
    # Enable WAL for concurrency
    await conn.execute("PRAGMA journal_mode=WAL;")
    # create settings table: guild_id, channel_id, emoji, rate_count, rate_seconds
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id INTEGER PRIMARY KEY,
            channel_id INTEGER,
            emoji TEXT,
            rate_count INTEGER DEFAULT ?,
            rate_seconds INTEGER DEFAULT ?
        )
        """,
        (DEFAULT_RATE_LIMIT_COUNT, DEFAULT_RATE_LIMIT_SECONDS),
    )
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
            "emoji": emoji,
            "rate_count": rate_count or DEFAULT_RATE_LIMIT_COUNT,
            "rate_seconds": rate_seconds or DEFAULT_RATE_LIMIT_SECONDS,
        }
    # defaults
    return {
        "channel_id": None,
        "emoji": "🔃",
        "rate_count": DEFAULT_RATE_LIMIT_COUNT,
        "rate_seconds": DEFAULT_RATE_LIMIT_SECONDS,
    }

async def set_guild_settings(guild_id: int, channel_id: Optional[int] = None, emoji: Optional[str] = None,
                             rate_count: Optional[int] = None, rate_seconds: Optional[int] = None):
    # upsert style
    conn = await aiosqlite.connect(DB_PATH)
    await conn.execute("INSERT OR IGNORE INTO guild_settings (guild_id, channel_id, emoji, rate_count, rate_seconds) VALUES (?, ?, ?, ?, ?)",
                       (guild_id, None, None, DEFAULT_RATE_LIMIT_COUNT, DEFAULT_RATE_LIMIT_SECONDS))
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
    logger.info("Updated settings for guild %s: channel=%s emoji=%s rate=%s/%s",
                guild_id, channel_id, emoji, rate_count, rate_seconds)

# ---------- Language utilities ----------
SUPPORTED_LANGS = {code.lower() for code in GOOGLE_LANGS.keys()}

async def refresh_libre_languages():
    """Fetch supported languages from LibreTranslate and merge into SUPPORTED_LANGS"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{LIBRE_URL}/languages", timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data:
                        code = item.get("code")
                        if code:
                            SUPPORTED_LANGS.add(code.lower())
                    logger.info("Fetched LibreTranslate supported languages.")
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
            # Libre doesn't always return detected language here; some instances may not include it.
            detected = data.get("detectedLanguage") or data.get("source") or None
            return data.get("translatedText", ""), detected

async def detect_libre(text: str) -> Optional[str]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{LIBRE_URL}/detect", json={"q": text}, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # returns e.g. [{"language":"en","confidence":0.8}]
                    if isinstance(data, list) and data:
                        return data[0].get("language")
    except Exception:
        return None
    return None

async def translate_google(text: str, dest: str) -> Tuple[str, Optional[str]]:
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: translator_google.translate(text, dest=dest))
    detected = getattr(result, "src", None)
    return getattr(result, "text", str(result)), detected

async def translate_text(text: str, dest: str) -> Tuple[str, Optional[str]]:
    dest = dest.lower()
    if TRANSLATE_PROVIDER == "libre":
        try:
            translated, detected = await translate_libre(text, dest)
            return translated, detected
        except Exception as e:
            logger.warning("LibreTranslate error, falling back to google: %s", e)
    # fallback
    try:
        return await translate_google(text, dest)
    except Exception as e:
        logger.exception("All translation providers failed: %s", e)
        raise

# ---------- Rate limiting ----------
def is_rate_limited(guild_id: int, user_id: int, limit_count: int, limit_seconds: int) -> bool:
    key = (guild_id, user_id)
    now = time.monotonic()
    timestamps = rate_map.get(key, [])
    # drop expired
    window = [t for t in timestamps if now - t <= limit_seconds]
    window.append(now)
    rate_map[key] = window
    return len(window) > limit_count

# ---------- Bot events & commands ----------
@bot.event
async def on_ready():
    logger.info("Logged in as %s (id: %s)", bot.user, bot.user.id)
    # ensure DB ready
    await init_db()
    # optionally refresh supported languages for libre
    if TRANSLATE_PROVIDER == "libre":
        asyncio.create_task(refresh_libre_languages())
    try:
        synced = await bot.tree.sync()
        logger.info("Synced %d commands", len(synced))
    except Exception as e:
        logger.exception("Failed to sync commands: %s", e)

# /setchannel admin-only
@bot.tree.command(name="setchannel", description="Set the translation reaction channel (Admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def setchannel(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return
    channels = [c for c in guild.text_channels if c.permissions_for(guild.me).send_messages]
    if not channels:
        await interaction.response.send_message("No channels available where I can send messages.", ephemeral=True)
        return
    options = [discord.SelectOption(label=c.name, description=f"Set {c.name}", value=str(c.id)) for c in channels[:25]]
    select = discord.ui.Select(placeholder="Select a translation channel", options=options)

    async def callback(inner: discord.Interaction):
        selected_channel_id = int(select.values[0])
        await set_guild_settings(guild.id, channel_id=selected_channel_id)
        await inner.response.send_message(f"✅ Translation channel set to <#{selected_channel_id}>", ephemeral=True)

    select.callback = callback
    view = discord.ui.View()
    view.add_item(select)
    await interaction.response.send_message("Choose a channel for translation reactions:", view=view, ephemeral=True)

@setchannel.error
async def setchannel_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("🚫 You need Administrator permissions to use this command.", ephemeral=True)
    else:
        logger.exception("setchannel error: %s", error)
        await interaction.response.send_message("❌ An error occurred.", ephemeral=True)

# /setemoji admin-only (per guild)
@bot.tree.command(name="setemoji", description="Set the reaction emoji used for triggering translations (Admin only)")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(emoji="An emoji character (e.g., 🔃 or 🈂️). Use a single emoji.")
async def setemoji(interaction: discord.Interaction, emoji: str):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return
    emoji = emoji.strip()
    if len(emoji) == 0:
        await interaction.response.send_message("Please specify an emoji.", ephemeral=True)
        return
    # Save it
    await set_guild_settings(guild.id, emoji=emoji)
    await interaction.response.send_message(f"✅ Reaction emoji set to `{emoji}`", ephemeral=True)

@setemoji.error
async def setemoji_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("🚫 You need Administrator permissions to use this command.", ephemeral=True)
    else:
        logger.exception("setemoji error: %s", error)
        await interaction.response.send_message("❌ An error occurred.", ephemeral=True)

# /setratelimit admin-only
@bot.tree.command(name="setratelimit", description="Set rate limit: how many translations per time window (Admin only)")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(count="Number of translations", seconds="Window in seconds")
async def setratelimit(interaction: discord.Interaction, count: int, seconds: int):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return
    if count < 1 or seconds < 1:
        await interaction.response.send_message("Values must be positive integers.", ephemeral=True)
        return
    await set_guild_settings(guild.id, rate_count=count, rate_seconds=seconds)
    await interaction.response.send_message(f"✅ Rate limit set to {count} translations per {seconds} seconds.", ephemeral=True)

@setratelimit.error
async def setratelimit_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("🚫 You need Administrator permissions to use this command.", ephemeral=True)
    else:
        logger.exception("setratelimit error: %s", error)
        await interaction.response.send_message("❌ An error occurred.", ephemeral=True)

# /translate command (instant)
@bot.tree.command(name="translate", description="Translate text to a target language")
@app_commands.describe(text="Text to translate", target="Language code (e.g., en, fr, de)")
async def slash_translate(interaction: discord.Interaction, text: str, target: str):
    await interaction.response.defer(ephemeral=True)
    target = target.strip().lower()
    if not await is_valid_lang(target):
        await interaction.followup.send("❌ Invalid or unsupported language code. Examples: `en`, `fr`, `de`, `es`.", ephemeral=True)
        return
    try:
        translated, detected = await translate_text(text, target)
        detected_info = f" (detected: {detected})" if detected else ""
        await interaction.followup.send(f"**Translation ({target}){detected_info}:**\n{translated}", ephemeral=True)
    except Exception as e:
        logger.exception("slash translate failed: %s", e)
        await interaction.followup.send(f"❌ Translation failed: {e}", ephemeral=True)

# React with configured emoji in configured channel(s)
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if not message.guild:
        return
    settings = await get_guild_settings(message.guild.id)
    channel_id = settings.get("channel_id")
    if channel_id and message.channel.id == channel_id:
        try:
            emoji = settings.get("emoji") or "🔃"
            await message.add_reaction(emoji)
        except Exception:
            logger.exception("Failed to add reaction to message %s", message.id)
    await bot.process_commands(message)

# Helper: attempt to fetch text from first attachment if it's a text-like file
async def fetch_attachment_text(attachment: discord.Attachment) -> Optional[str]:
    # naive check: common text file extensions or content-type header in URL
    text_exts = (".txt", ".md", ".csv", ".log")
    if any(str(attachment.filename).lower().endswith(ext) for ext in text_exts):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url, timeout=15) as resp:
                    if resp.status == 200:
                        return await resp.text()
        except Exception as e:
            logger.debug("Failed to fetch attachment text: %s", e)
    return None

@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
    try:
        if user.bot:
            return
        msg = reaction.message
        if not msg.guild:
            return  # only server messages
        settings = await get_guild_settings(msg.guild.id)
        config_emoji = settings.get("emoji") or "🔃"
        if str(reaction.emoji) != str(config_emoji):
            return
        if msg.channel.id != settings.get("channel_id"):
            return

        # rate limiting
        limit_count = settings.get("rate_count", DEFAULT_RATE_LIMIT_COUNT)
        limit_seconds = settings.get("rate_seconds", DEFAULT_RATE_LIMIT_SECONDS)
        if is_rate_limited(msg.guild.id, user.id, limit_count, limit_seconds):
            try:
                await user.send(f"🚫 You're being rate-limited: max {limit_count} translations per {limit_seconds} seconds in this server.")
            except Exception:
                logger.debug("Couldn't DM user about rate-limit")
            try:
                await reaction.remove(user)
            except Exception:
                pass
            return

        # remove user's reaction for tidiness (best-effort)
        try:
            await reaction.remove(user)
        except Exception:
            logger.debug("Couldn't remove user's reaction; missing perms?")

        # prepare content: priority -> message.content, then attachment text
        content_to_translate = msg.content or ""
        if not content_to_translate and msg.attachments:
            # attempt to fetch text from first attachment
            fetched = await fetch_attachment_text(msg.attachments[0])
            if fetched:
                content_to_translate = fetched
            else:
                # unsupported attachment type (image/pdf) — notify the user
                try:
                    await user.send("⚠️ This attachment type isn't supported for translation yet (no OCR). Please copy/paste the text or attach a .txt file.")
                except Exception:
                    logger.debug("Couldn't DM user about unsupported attachment.")
                return

        if not content_to_translate:
            try:
                await user.send("⚠️ There's no text to translate in that message.")
            except Exception:
                logger.debug("Couldn't DM user about empty content.")
            return

        # DM user to ask for target language
        try:
            dm = await user.create_dm()
            await dm.send("🌐 Please reply with a language code (e.g., `en` for English). Reply within 60 seconds.")

            def check(m: discord.Message):
                return m.author.id == user.id and isinstance(m.channel, discord.DMChannel)

            reply = await bot.wait_for("message", check=check, timeout=60)
            lang = reply.content.strip().lower()

            if not await is_valid_lang(lang):
                await dm.send("❌ Invalid language code. Example codes: `en`, `fr`, `de`, `es`.")
                return

            # perform translation asynchronously
            translated_text, detected = await translate_text(content_to_translate, lang)
            detected_info = f"Detected source language: {detected}\n\n" if detected else ""
            # chunk the response if long (Discord DM limit ~2000 chars)
            message_body = f"✅ **Translated Message ({lang}):**\n\n{translated_text}"
            if detected_info:
                message_body = f"{detected_info}{message_body}"

            # send in DM (chunk if necessary)
            for chunk_start in range(0, len(message_body), 1900):
                await dm.send(message_body[chunk_start:chunk_start + 1900])

        except asyncio.TimeoutError:
            try:
                await user.send("⌛ Translation request timed out. React again with the configured emoji to retry.")
            except Exception:
                logger.debug("Couldn't DM user about timeout.")
        except Exception as e:
            logger.exception("Error during translation flow: %s", e)
            try:
                await user.send(f"❌ Error during translation: {e}")
            except Exception:
                logger.debug("Couldn't DM user about translation error.")

    except Exception:
        logger.exception("Unhandled error in on_reaction_add")

# ---------- Graceful shutdown ----------
async def shutdown():
    logger.info("Shutting down.")
    # nothing special to close for aiosqlite since we open/close per operation

def run():
    try:
        asyncio.run(init_db())
        bot.run(TOKEN)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt. Exiting.")
        try:
            asyncio.run(shutdown())
        except Exception:
            pass

if __name__ == "__main__":
    run()
