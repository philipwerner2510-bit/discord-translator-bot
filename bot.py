# bot.py
import os
import asyncio
import discord
from discord.ext import commands
from datetime import datetime, timedelta
from utils import database

BOT_COLOR = 0xDE002A
PRESENCE_INTERVAL = 300  # seconds

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.reactions = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot.start_time = datetime.utcnow()
bot.total_translations = 0


# -----------------------------
# Setup hook: init DB + load cogs
# -----------------------------
async def setup_hook():
    await database.init_db()

    extensions = [
        "cogs.user_commands",
        "cogs.admin_commands",
        "cogs.translate",
        "cogs.events",
        "cogs.ops_commands",
        "cogs.analytics_commands", 
        "cogs.welcome.py",
    ]
    for ext in extensions:
        try:
            await bot.load_extension(ext)
            print(f"✅ Loaded {ext}")
        except Exception as e:
            print(f"❌ Failed to load {ext}: {e}")

# IMPORTANT: register the hook so discord.py actually calls it
bot.setup_hook = setup_hook


# -----------------------------
# Ready: per-guild + global sync
# -----------------------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")

    # Fast per-guild sync so commands show instantly
    synced = 0
    for guild in bot.guilds:
        try:
            await bot.tree.sync(guild=guild)
            print(f"🔧 Synced commands to guild {guild.name} ({guild.id})")
            synced += 1
        except Exception as e:
            print(f"❌ Sync failed in guild {guild.id}: {e}")
    print(f"✅ Per-guild sync completed for {synced} guilds")

    # Also do a global sync (helps future guilds)
    try:
        await bot.tree.sync()
        print("🌍 Global slash commands synced")
    except Exception as e:
        print(f"⚠️ Global sync error: {e}")

    # background tasks
    asyncio.create_task(update_presence())
    asyncio.create_task(reset_daily_translations())
    print("Instance is healthy ✅")


# -----------------------------
# Sync when joining a new guild
# -----------------------------
@bot.event
async def on_guild_join(guild: discord.Guild):
    try:
        await bot.tree.sync(guild=guild)
        print(f"🆕 Synced commands to NEW guild {guild.name} ({guild.id})")
    except Exception as e:
        print(f"❌ Failed syncing new guild {guild.id}: {e}")

    # Try coloring the bot's top role (if not managed)
    try:
        role = guild.me.top_role
        if role and not role.managed:
            await role.edit(color=discord.Color(BOT_COLOR))
    except Exception:
        pass


# -----------------------------
# Presence updater
# -----------------------------
async def update_presence():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            activity = discord.Game(
                name=f"{len(bot.guilds)} servers | {bot.total_translations} translated"
            )
            await bot.change_presence(activity=activity)
        except Exception as e:
            print(f"⚠️ Presence update failed: {e}")
        await asyncio.sleep(PRESENCE_INTERVAL)


# -----------------------------
# Reset daily translation counter at 00:00 UTC
# -----------------------------
async def reset_daily_translations():
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.utcnow()
        next_reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        await asyncio.sleep(max(1.0, (next_reset - now).total_seconds()))
        bot.total_translations = 0
        print("🔄 Daily translation counter reset")


# -----------------------------
# Entrypoint
# -----------------------------
if __name__ == "__main__":
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Missing BOT_TOKEN environment variable.")
    bot.run(token)