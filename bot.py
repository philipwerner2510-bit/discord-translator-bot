import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import aiohttp
import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from googletrans import Translator as GoogleTranslator
from googletrans import LANGUAGES as GOOGLE_LANGS

# ---------- Config ----------
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN env variable is required.")

DB_PATH = Path("data.db")
DEFAULT_RATE_COUNT = int(os.getenv("DEFAULT_RATE_COUNT", 5))
DEFAULT_RATE_SECONDS = int(os.getenv("DEFAULT_RATE_SECONDS", 60))
LIBRE_URL = "https://libretranslate.com"

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("translator-bot")

# ---------- Bot setup ----------
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.reactions = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)
translator_google = GoogleTranslator()

# ---------- Rate limit storage ----------
rate_map: Dict[Tuple[int, int], list] = {}  # (guild_id, user_id) -> timestamps

# ---------- DB helpers ----------
async def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(DB_PATH)
    await conn.execute("PRAGMA journal_mode=WAL;")
    await conn.execute(f"""
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id INTEGER PRIMARY KEY,
            channels TEXT,
            emoji TEXT DEFAULT '🔃',
            rate_count INTEGER DEFAULT {DEFAULT_RATE_COUNT},
            rate_seconds INTEGER DEFAULT {DEFAULT_RATE_SECONDS},
            error_channel INTEGER
        )
    """)
    await conn.commit()
    await conn.close()
    logger.info("Database initialized.")

async def get_guild_settings(guild_id: int) -> dict:
    conn = await aiosqlite.connect(DB_PATH)
    row = await conn.execute_fetchone(
        "SELECT channels, emoji, rate_count, rate_seconds, error_channel FROM guild_settings WHERE guild_id = ?",
        (guild_id,)
    )
    await conn.close()
    if row:
        channels_str, emoji, rate_count, rate_seconds, error_channel = row
        channels = [int(c) for c in channels_str.split(",")] if channels_str else []
        return {
            "channels": channels,
            "emoji": emoji or "🔃",
            "rate_count": rate_count or DEFAULT_RATE_COUNT,
            "rate_seconds": rate_seconds or DEFAULT_RATE_SECONDS,
            "error_channel": error_channel
        }
    return {
        "channels": [],
        "emoji": "🔃",
        "rate_count": DEFAULT_RATE_COUNT,
        "rate_seconds": DEFAULT_RATE_SECONDS,
        "error_channel": None
    }

async def set_guild_settings(guild_id: int, channels: Optional[List[int]] = None,
                             emoji: Optional[str] = None, rate_count: Optional[int] = None,
                             rate_seconds: Optional[int] = None, error_channel: Optional[int] = None):
    conn = await aiosqlite.connect(DB_PATH)
    await conn.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild_id,))
    if channels is not None:
        channels_str = ",".join(str(c) for c in channels)
        await conn.execute("UPDATE guild_settings SET channels = ? WHERE guild_id = ?", (channels_str, guild_id))
    if emoji is not None:
        await conn.execute("UPDATE guild_settings SET emoji = ? WHERE guild_id = ?", (emoji, guild_id))
    if rate_count is not None:
        await conn.execute("UPDATE guild_settings SET rate_count = ? WHERE guild_id = ?", (rate_count, guild_id))
    if rate_seconds is not None:
        await conn.execute("UPDATE guild_settings SET rate_seconds = ? WHERE guild_id = ?", (rate_seconds, guild_id))
    if error_channel is not None:
        await conn.execute("UPDATE guild_settings SET error_channel = ? WHERE guild_id = ?", (error_channel, guild_id))
    await conn.commit()
    await conn.close()

# ---------- Translation ----------
SUPPORTED_LANGS = {code.lower() for code in GOOGLE_LANGS.keys()}

async def translate_google(text: str, dest: str):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: translator_google.translate(text, dest=dest))
    return getattr(result, "text", str(result)), getattr(result, "src", None)

async def translate_libre(text: str, dest: str, source: str = "auto"):
    payload = {"q": text, "source": source, "target": dest, "format": "text"}
    headers = {"Accept": "application/json"}
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{LIBRE_URL}/translate", json=payload, headers=headers, timeout=20) as resp:
            if resp.status != 200:
                txt = await resp.text()
                raise RuntimeError(f"LibreTranslate error {resp.status}: {txt}")
            data = await resp.json()
            detected = data.get("detectedLanguage") or None
            return data.get("translatedText", ""), detected

async def translate_text(text: str, dest: str):
    try:
        return await translate_google(text, dest)
    except Exception as e:
        logger.warning("Google failed, falling back to LibreTranslate: %s", e)
        try:
            return await translate_libre(text, dest)
        except Exception as e2:
            logger.error("LibreTranslate failed too: %s", e2)
            raise RuntimeError("Both translation providers failed.")

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
    logger.info(f"✅ Logged in as {bot.user}")
    await init_db()
    try:
        synced = await bot.tree.sync()
        logger.info(f"✅ Synced {len(synced)} commands")
    except Exception as e:
        logger.exception(f"Sync failed: {e}")

@bot.event
async def on_disconnect():
    logger.warning("Bot disconnected. Will auto-reconnect.")

@bot.event
async def on_resumed():
    logger.info("Bot reconnected successfully.")

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return
    try:
        settings = await get_guild_settings(message.guild.id)
        if message.channel.id in settings["channels"]:
            await message.add_reaction(settings["emoji"])
    except Exception as e:
        await log_error(message.guild.id, f"on_message error: {e}")
    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or not reaction.message.guild:
        return
    try:
        settings = await get_guild_settings(reaction.message.guild.id)
        if reaction.message.channel.id not in settings["channels"]:
            return
        if str(reaction.emoji) != settings["emoji"]:
            return

        if is_rate_limited(reaction.message.guild.id, user.id, settings["rate_count"], settings["rate_seconds"]):
            await reaction.remove(user)
            await user.send(f"🚫 Rate limit reached ({settings['rate_count']}/{settings['rate_seconds']}s).")
            return

        await reaction.remove(user)
        await user.send("🌐 Reply with a language code (e.g., en, fr):")
        def check(m): return m.author == user and isinstance(m.channel, discord.DMChannel)
        reply = await bot.wait_for("message", check=check, timeout=60)
        lang = reply.content.strip().lower()
        if lang not in SUPPORTED_LANGS:
            await user.send("❌ Invalid language code.")
            return
        translated, detected = await translate_text(reaction.message.content, lang)
        msg = f"✅ **Translated ({lang})**\nDetected: `{detected}`\n\n{translated}" if detected else f"✅ **Translated ({lang})**\n\n{translated}"
        await user.send(msg)
    except Exception as e:
        await log_error(reaction.message.guild.id, f"on_reaction_add error: {e}")

# ---------- Error logging ----------
async def log_error(guild_id: int, msg: str):
    settings = await get_guild_settings(guild_id)
    channel_id = settings.get("error_channel")
    if not channel_id:
        logger.error(f"[Guild {guild_id}] {msg}")
        return
    channel = bot.get_channel(channel_id)
    if channel:
        try:
            await channel.send(f"⚠️ Error: {msg}")
        except Exception as e:
            logger.error(f"Failed to send error log: {e}")

# ---------- Slash commands ----------
@bot.tree.command(name="addchannel", description="Add a channel for translation reactions")
@app_commands.checks.has_permissions(administrator=True)
async def addchannel(interaction: discord.Interaction):
    guild = interaction.guild
    channels = [c for c in guild.text_channels if c.permissions_for(guild.me).send_messages]
    options = [discord.SelectOption(label=c.name, value=str(c.id)) for c in channels[:25]]
    select = discord.ui.Select(placeholder="Select channel to add", options=options)

    async def callback(inner: discord.Interaction):
        cid = int(select.values[0])
        settings = await get_guild_settings(guild.id)
        channels_list = settings["channels"]
        if cid not in channels_list:
            channels_list.append(cid)
        await set_guild_settings(guild.id, channels=channels_list)
        await inner.response.send_message(f"✅ Channel <#{cid}> added for translations.", ephemeral=True)

    select.callback = callback
    view = discord.ui.View()
    view.add_item(select)
    await interaction.response.send_message("Select a channel:", view=view, ephemeral=True)

@bot.tree.command(name="setemoji", description="Set the reaction emoji")
@app_commands.checks.has_permissions(administrator=True)
async def setemoji(interaction: discord.Interaction, emoji: str):
    await set_guild_settings(interaction.guild.id, emoji=emoji)
    await interaction.response.send_message(f"✅ Emoji set to {emoji}", ephemeral=True)

@bot.tree.command(name="seterrorchannel", description="Set the error logging channel")
@app_commands.checks.has_permissions(administrator=True)
async def seterrorchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    await set_guild_settings(interaction.guild.id, error_channel=channel.id)
    await interaction.response.send_message(f"✅ Error logging channel set to <#{channel.id}>", ephemeral=True)

@bot.tree.command(name="help", description="Show bot commands")
async def help_command(interaction: discord.Interaction):
    help_text = (
        "**Translator Bot Commands:**\n"
        "/addchannel - Add a channel for translation reactions\n"
        "/setemoji - Set reaction emoji\n"
        "/seterrorchannel - Set error logging channel\n"
        "/help - Show this help message\n"
        "React with the emoji in a translation channel to translate a message privately.\n"
        "Uses Google Translate first, then public LibreTranslate as fallback."
    )
    await interaction.response.send_message(help_text, ephemeral=True)

# ---------- Run ----------
if __name__ == "__main__":
    bot.run(TOKEN, reconnect=True)
