# bot.py
import os
import asyncio
import traceback
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from utils import database

BOT_COLOR = 0xDE002A
PRESENCE_INTERVAL = 300  # 5 minutes

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.reactions = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Runtime counters (reset daily at 00:00 UTC)
bot.total_translations = 0
bot.libre_translations = 0
bot.ai_translations = 0
bot.cache_hits = 0
bot.cache_misses = 0

# -----------------------------
# Extensions to load
# -----------------------------
EXTENSIONS = [
    "cogs.user_commands",
    "cogs.admin_commands",
    "cogs.translate",
    "cogs.events",
    "cogs.ops_commands",
    "cogs.analytics_commands",
    "cogs.welcome",
    "cogs.owner_commands",  # keep last so failures here don't block others
]

# -----------------------------
# Presence loop (every 5 min)
# -----------------------------
async def presence_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            guild_count = len(bot.guilds)
            total_trans = getattr(bot, "total_translations", 0)
            activity = discord.Game(name=f"{guild_count} servers • {total_trans} translations today")
            await bot.change_presence(activity=activity)
        except Exception as e:
            print(f"⚠️ Presence update failed: {e}")
        await asyncio.sleep(PRESENCE_INTERVAL)

# -----------------------------
# Daily reset at 00:00 UTC
# -----------------------------
async def reset_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.utcnow()
        next_reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        await asyncio.sleep((next_reset - now).total_seconds())
        bot.total_translations = 0
        bot.libre_translations = 0
        bot.ai_translations = 0
        bot.cache_hits = 0
        bot.cache_misses = 0
        print("🔄 Daily counters reset")

# -----------------------------
# on_ready: sync commands & start loops
# -----------------------------
@bot.event
async def on_ready():
    # Sync global commands
    try:
        await bot.tree.sync()
        print("🌍 Global slash commands synced")
    except Exception as e:
        print(f"❌ Global sync failed: {type(e).__name__}: {e}")
        traceback.print_exc()

    print(f"✅ Logged in as {bot.user} ({bot.user.id})")

    # Start background tasks once
    if not getattr(bot, "_presence_task", None):
        bot._presence_task = asyncio.create_task(presence_loop())
    if not getattr(bot, "_reset_task", None):
        bot._reset_task = asyncio.create_task(reset_loop())

# -----------------------------
# Diagnostics helper
# -----------------------------
def print_dependency_versions():
    try:
        import openai  # type: ignore
        import httpx   # type: ignore
        print(f"✅ Dependencies: openai={getattr(openai, '__version__', 'unknown')} | httpx={getattr(httpx, '__version__', 'unknown')}")
    except Exception as e:
        print(f"⚠️ Could not read dependency versions: {e}")

def print_config_preview():
    libre_base = os.getenv("LIBRE_BASE")
    openai_model = os.getenv("OPENAI_MODEL")
    print("✅ Config loaded.")
    if libre_base:
        print(f"• LIBRE_BASE={libre_base}")
    if openai_model:
        print(f"• OPENAI_MODEL={openai_model}")

# -----------------------------
# Main: init DB, load cogs, run
# -----------------------------
async def main():
    print_config_preview()
    await database.init_db()

    async with bot:
        for ext in EXTENSIONS:
            try:
                await bot.load_extension(ext)
                print(f"✅ Loaded {ext}")
            except Exception as e:
                print(f"❌ Failed to load {ext}: {type(e).__name__}: {e}")
                traceback.print_exc()

        # Token required
        token = os.environ.get("BOT_TOKEN")
        if not token:
            raise RuntimeError("BOT_TOKEN is not set")

        print_dependency_versions()
        await bot.start(token)

# -----------------------------
# Entrypoint
# -----------------------------
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Shutting down")