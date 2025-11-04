import os
import asyncio
from datetime import datetime, timedelta

import discord
from discord.ext import commands

# -----------------------------
# Intents
# -----------------------------
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.reactions = True
intents.message_content = True
intents.dm_messages = True

# -----------------------------
# Bot
# -----------------------------
bot = commands.Bot(command_prefix="!", intents=intents)

# -----------------------------
# Runtime counters (reset on restart)
# -----------------------------
bot.total_translations = 0
bot.cached_translations = 0
bot.cache_hits = 0
bot.cache_misses = 0
bot.ai_translations = 0
bot.libre_translations = 0

# Color & presence
BOT_COLOR = 0xDE002A
PRESENCE_INTERVAL = 300  # seconds

# Optional: speed up dev by syncing to a specific guild first (string ID)
DEV_GUILD_ID = os.getenv("DEV_GUILD_ID")  # e.g. "1425585153585189067"


# -----------------------------
# Local slash: /test
# -----------------------------
@bot.tree.command(name="test", description="Quick check that the bot is alive and commands are synced.")
async def test_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("✅ Test command works!", ephemeral=True)


# -----------------------------
# Cog loader & runner
# -----------------------------
async def run():
    cogs = [
        "cogs.user_commands",
        "cogs.admin_commands",
        "cogs.translate",
        "cogs.events",
        "cogs.ops_commands",
        "cogs.analytics_commands",  # keep if present
        "cogs.welcome",             # keep if present
    ]
    for ext in cogs:
        try:
            await bot.load_extension(ext)
            print(f"✅ Loaded {ext}")
        except Exception as e:
            print(f"❌ Failed to load {ext}: {e}")

    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN env var is missing.")
    await bot.start(token)


# -----------------------------
# Slash sync + background loops
# -----------------------------
@bot.event
async def on_ready():
    # ✅ Dependency version check (OpenAI + httpx)
    try:
        import httpx, openai
        print(f"✅ Dependencies: openai={openai.__version__} | httpx={httpx.__version__}")
    except Exception as e:
        print(f"⚠️ Dependency version check failed: {e}")

    bot.start_time = getattr(bot, "start_time", datetime.utcnow())

    # Per-guild dev sync (if provided), then global sync
    try:
        if DEV_GUILD_ID:
            gid = int(DEV_GUILD_ID)
            guild = discord.Object(id=gid)
            synced = await bot.tree.sync(guild=guild)
            print(f"🔧 Synced commands to guild {gid} ({len(synced)} cmds)")
        synced_global = await bot.tree.sync()
        print(f"🌍 Global slash commands synced ({len(synced_global)} cmds)")
    except Exception as e:
        print(f"⚠️ Command sync failed: {e}")

    print(f"✅ Logged in as {bot.user} ({bot.user.id})")

    # Presence loop
    if not getattr(bot, "_presence_task", None):
        bot._presence_task = asyncio.create_task(presence_loop())

    # Daily counter reset (translations today)
    if not getattr(bot, "_daily_reset_task", None):
        bot._daily_reset_task = asyncio.create_task(daily_reset())

    print("Instance is healthy ✅")


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


async def daily_reset():
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.utcnow()
        next_reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        await asyncio.sleep(max(1, (next_reset - now).total_seconds()))
        bot.total_translations = 0
        print("🔄 Daily translations counter reset")


# -----------------------------
# Entry
# -----------------------------
if __name__ == "__main__":
    asyncio.run(run())