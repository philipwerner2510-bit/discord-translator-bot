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

# ---------- Database helpers ----------
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
            error_channel INTEGER,
            default_lang TEXT
        )
    """)
    await conn.execute(f"""
        CREATE TABLE IF NOT EXISTS user_settings (
            guild_id INTEGER,
            user_id INTEGER,
            default_lang TEXT,
            PRIMARY KEY (guild_id, user_id)
        )
    """)
    await conn.commit()
    await conn.close()
    logger.info("Database initialized.")

async def get_guild_settings(guild_id: int) -> dict:
    conn = await aiosqlite.connect(DB_PATH)
    cursor = await conn.execute(
        "SELECT channels, emoji, rate_count, rate_seconds, error_channel, default_lang FROM guild_settings WHERE guild_id = ?",
        (guild_id,)
    )
    row = await cursor.fetchone()
    await cursor.close()
    await conn.close()
    if row:
        channels_str, emoji, rate_count, rate_seconds, error_channel, default_lang = row
        channels = [int(c) for c in channels_str.split(",")] if channels_str else []
        return {
            "channels": channels,
            "emoji": emoji or "🔃",
            "rate_count": rate_count or DEFAULT_RATE_COUNT,
            "rate_seconds": rate_seconds or DEFAULT_RATE_SECONDS,
            "error_channel": error_channel,
            "default_lang": default_lang
        }
    return {
        "channels": [],
        "emoji": "🔃",
        "rate_count": DEFAULT_RATE_COUNT,
        "rate_seconds": DEFAULT_RATE_SECONDS,
        "error_channel": None,
        "default_lang": None
    }

async def set_guild_settings(guild_id: int, channels: Optional[List[int]] = None,
                             emoji: Optional[str] = None, rate_count: Optional[int] = None,
                             rate_seconds: Optional[int] = None, error_channel: Optional[int] = None,
                             default_lang: Optional[str] = None):
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
    if default_lang is not None:
        await conn.execute("UPDATE guild_settings SET default_lang = ? WHERE guild_id = ?", (default_lang, guild_id))
    await conn.commit()
    await conn.close()

async def get_user_settings(guild_id: int, user_id: int) -> dict:
    conn = await aiosqlite.connect(DB_PATH)
    cursor = await conn.execute(
        "SELECT default_lang FROM user_settings WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )
    row = await cursor.fetchone()
    await cursor.close()
    await conn.close()
    return {"default_lang": row[0]} if row else {}

async def set_user_settings(guild_id: int, user_id: int, default_lang: str):
    conn = await aiosqlite.connect(DB_PATH)
    await conn.execute(
        "INSERT OR REPLACE INTO user_settings (guild_id, user_id, default_lang) VALUES (?, ?, ?)",
        (guild_id, user_id, default_lang)
    )
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
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    translated_total = ""
    detected_total = None
    for chunk in chunks:
        try:
            translated, detected = await translate_google(chunk, dest)
        except Exception as e:
            logger.warning("Google failed, falling back to LibreTranslate: %s", e)
            translated, detected = await translate_libre(chunk, dest)
        translated_total += translated
        if detected and not detected_total:
            detected_total = detected
    return translated_total, detected_total

# ---------- Rate limiting ----------
def is_rate_limited(guild_id: int, user_id: int, limit_count: int, limit_seconds: int) -> bool:
    key = (guild_id, user_id)
    now = time.monotonic()
    window = [t for t in rate_map.get(key, []) if now - t <= limit_seconds]
    window.append(now)
    rate_map[key] = window
    return len(window) > limit_count

# ---------- Error logging ----------
async def log_error(guild_id: Optional[int], message: str):
    logger.error(f"[Guild {guild_id}] {message}")
    if guild_id:
        settings = await get_guild_settings(guild_id)
        channel_id = settings.get("error_channel")
        if channel_id:
            channel = bot.get_channel(channel_id)
            if channel:
                embed = discord.Embed(
                    title="Error",
                    description=message,
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow()
                )
                await channel.send(embed=embed)

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
            try:
                await message.add_reaction(settings["emoji"])
            except discord.Forbidden:
                pass
    except Exception as e:
        await log_error(message.guild.id, f"on_message error: {e}")
    await bot.process_commands(message)

# ---------- on_reaction_add continues ----------
    try:
        settings = await get_guild_settings(reaction.message.guild.id)
        if reaction.message.channel.id not in settings["channels"]:
            return
        if str(reaction.emoji) != settings["emoji"]:
            return

        if is_rate_limited(reaction.message.guild.id, user.id, settings["rate_count"], settings["rate_seconds"]):
            try:
                await reaction.remove(user)
            except discord.Forbidden:
                pass
            await user.send(f"🚫 Rate limit reached ({settings['rate_count']} per {settings['rate_seconds']}s).")
            return

        await reaction.remove(user)  # remove reaction immediately

        # Ask user for language
        try:
            await user.send("🌐 Please reply with a language code (e.g., `en`, `fr`, `de`):")

            def check(m):
                return m.author == user and isinstance(m.channel, discord.DMChannel)

            reply = await bot.wait_for("message", check=check, timeout=60)
            lang = reply.content.strip().lower()
            if lang not in SUPPORTED_LANGS:
                await user.send(f"❌ Invalid language code. Supported codes: {', '.join(list(SUPPORTED_LANGS)[:50])}...")
                return

            # Store user preference (overwrites server default)
            await set_user_settings(reaction.message.guild.id, user.id, lang)

            translated, detected = await translate_text(reaction.message.content, lang)

            # Create embed for original message
            embed = discord.Embed(
                title="Original Message",
                description=reaction.message.content,
                color=discord.Color(int("de002a", 16))
            )
            embed.set_author(name=reaction.message.author.display_name,
                             icon_url=reaction.message.author.display_avatar.url)
            footer_text = f"Translated to {lang}"
            if detected:
                footer_text += f" | Detected: {detected}"
            embed.set_footer(text=footer_text)

            # Send to user
            await user.send(embed=embed)
            await user.send(translated)

        except asyncio.TimeoutError:
            await user.send("❌ Timeout. You did not respond in time.")
        except Exception as e:
            await log_error(reaction.message.guild.id, f"on_reaction_add inner error: {e}")
            await user.send(f"❌ Error during translation: {e}")

    except Exception as e:
        await log_error(reaction.message.guild.id, f"on_reaction_add outer error: {e}")


# ---------- Slash Commands ----------

@bot.tree.command(name="setmylang", description="Set your personal default translation language")
async def setmylang(interaction: discord.Interaction, lang: str):
    lang = lang.lower()
    if lang not in SUPPORTED_LANGS:
        await interaction.response.send_message(f"❌ Invalid language code. Example: `en`, `fr`, `de`", ephemeral=True)
        return
    await set_user_settings(interaction.guild.id, interaction.user.id, lang)
    await interaction.response.send_message(f"✅ Your personal translation language has been set to `{lang}`.", ephemeral=True)


@bot.tree.command(name="channelselection", description="Admin: Select which channels the bot should react in")
@app_commands.checks.has_permissions(administrator=True)
async def channelselection(interaction: discord.Interaction):
    guild = interaction.guild
    channels = [c for c in guild.text_channels if c.permissions_for(guild.me).send_messages]

    options = [
        discord.SelectOption(label=c.name, value=str(c.id))
        for c in channels[:25]
    ]

    select = discord.ui.Select(
        placeholder="Select channels for translation reactions",
        options=options,
        min_values=1,
        max_values=len(options)
    )

    async def callback(inner_interaction: discord.Interaction):
        selected_ids = [int(v) for v in select.values]
        await set_guild_settings(guild.id, channels=selected_ids)
        await inner_interaction.response.send_message(
            f"✅ Translation channels updated: {', '.join(f'<#{c}>' for c in selected_ids)}",
            ephemeral=True
        )

    select.callback = callback
    view = discord.ui.View()
    view.add_item(select)
    await interaction.response.send_message("Select channels for translation reactions:", view=view, ephemeral=True)

# ---------- /translate command ----------
@bot.tree.command(name="translate", description="Translate a message manually")
async def translate(interaction: discord.Interaction, text: str, lang: str):
    lang = lang.lower()
    if lang not in SUPPORTED_LANGS:
        await interaction.response.send_message(f"❌ Invalid language code. Example: `en`, `fr`, `de`", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)  # in case translation takes time
    try:
        translated, detected = await translate_text(text, lang)

        # Embed for original text
        embed = discord.Embed(
            title="Original Text",
            description=text,
            color=discord.Color(int("de002a", 16))
        )
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        footer_text = f"Translated to {lang}"
        if detected:
            footer_text += f" | Detected: {detected}"
        embed.set_footer(text=footer_text)

        await interaction.followup.send(embed=embed)
        await interaction.followup.send(translated)

    except Exception as e:
        await log_error(interaction.guild.id if interaction.guild else None, f"/translate error: {e}")
        await interaction.followup.send(f"❌ Error during translation: {e}", ephemeral=True)


# ---------- /help command ----------
@bot.tree.command(name="help", description="Show all available commands")
async def help_command(interaction: discord.Interaction):
    is_admin = interaction.user.guild_permissions.administrator
    embed = discord.Embed(
        title="Translator Bot Commands",
        color=discord.Color(int("de002a", 16))
    )

    # Always available commands
    embed.add_field(name="/setmylang <lang>", value="Set your personal translation language.", inline=False)

    if is_admin:
        # Admin-only commands
        embed.add_field(name="/channelselection", value="Select which channels the bot reacts in.", inline=False)
        embed.add_field(name="/translate <text> <lang>", value="Manually translate any text.", inline=False)
    else:
        # Non-admin users only see setmylang
        pass  # already added above

    await interaction.response.send_message(embed=embed, ephemeral=True)


# ---------- Run Bot ----------
if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except Exception as e:
        logger.exception(f"Bot failed to start: {e}")
