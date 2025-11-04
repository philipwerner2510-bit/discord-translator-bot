import os
import asyncio
import discord
from discord.ext import commands
from datetime import datetime, timedelta
from utils import database

BOT_COLOR = 0xDE002A
PRESENCE_INTERVAL = 300

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.reactions = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)
bot.start_time = datetime.utcnow()
bot.total_translations = 0

async def setup_hook():
    await database.init_db()
    extensions = (
        "cogs.user_commands",
        "cogs.admin_commands",
        "cogs.translate",
        "cogs.events",
        "cogs.ops_commands",
        "cogs.analytics_commands",
    )
    for ext in extensions:
        try:
            await bot.load_extension(ext)
            print(f"✅ Loaded {ext}")
        except Exception as e:
            print(f"❌ Failed to load {ext}: {e}")

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")
    await bot.tree.sync()
    print("✅ Slash commands synced")
    asyncio.create_task(update_presence())
    asyncio.create_task(reset_daily_translations())
    print("Instance is healthy")

async def update_presence():
    await bot.wait_until_ready()
    while True:
        try:
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(bot.guilds)} servers | {bot.total_translations} translated"
            )
            await bot.change_presence(activity=activity)
        except Exception as e:
            print(f"⚠️ Presence update failed: {e}")
        await asyncio.sleep(PRESENCE_INTERVAL)

async def reset_daily_translations():
    await bot.wait_until_ready()
    while True:
        now = datetime.utcnow()
        next_ = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        await asyncio.sleep((next_ - now).total_seconds())
        bot.total_translations = 0
        print("🔄 Daily counter reset")

if __name__ == "__main__":
    bot.run(os.environ["BOT_TOKEN"])