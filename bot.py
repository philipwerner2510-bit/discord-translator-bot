import os
import asyncio
import discord
from discord.ext import commands
from utils import database
from utils.brand import COLOR, NAME
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.reactions = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot.total_translations = 0

COGS = [
    "cogs.user_commands",
    "cogs.admin_commands",
    "cogs.translate",
    "cogs.events",
    "cogs.ops_commands",
    "cogs.analytics_commands",
    "cogs.invite_command",
    "cogs.welcome",
    "cogs.owner_commands",
    "cogs.context_menu",
]

async def setup_hook():
    await database.init()
    for ext in COGS:
        try:
            await bot.load_extension(ext)
            print(f"✅ Loaded {ext}")
        except Exception as e:
            print(f"❌ Failed to load {ext}: {e}")

@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
        print("🌍 Global slash commands synced")
    except Exception as e:
        print(f"Slash sync error: {e}")
    print(f"✅ Logged in as {bot.user} — {NAME}")
    if not hasattr(bot, "_presence_task"):
        bot._presence_task = asyncio.create_task(update_presence())
    if not hasattr(bot, "_daily_reset_task"):
        bot._daily_reset_task = asyncio.create_task(daily_reset_translations())

async def update_presence():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            guild_count = len(bot.guilds)
            total_trans = getattr(bot, "total_translations", 0)
            activity = discord.Game(name=f"{guild_count} servers • {total_trans} translations today")
            await bot.change_presence(activity=activity)
        except Exception as e:
            print(f"Presence update failed: {e}")
        await asyncio.sleep(300)

async def daily_reset_translations():
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.utcnow()
        next_reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        await asyncio.sleep((next_reset - now).total_seconds())
        bot.total_translations = 0
        print("🔄 Daily translations counter reset")

if __name__ == "__main__":
    async def main():
        async with bot:
            await setup_hook()
            token = os.environ["BOT_TOKEN"]
            await bot.start(token)
    asyncio.run(main())
