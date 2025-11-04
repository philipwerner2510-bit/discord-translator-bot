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

    extensions = [
        "cogs.user_commands",
        "cogs.admin_commands",
        "cogs.translate",
        "cogs.events",
        "cogs.ops_commands",
        "cogs.analytics_commands",
    ]

    for ext in extensions:
        try:
            await bot.load_extension(ext)
            print(f"✅ Loaded {ext}")
        except Exception as e:
            print(f"❌ Failed to load {ext}: {e}")


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")

    # 🔧 Fast per-guild slash command sync
    synced = 0
    for guild in bot.guilds:
        try:
            await bot.tree.sync(guild=guild)
            print(f"🔧 Synced commands to guild {guild.name} ({guild.id})")
            synced += 1
        except Exception as e:
            print(f"❌ Sync failed in guild {guild.id}: {e}")

    print(f"✅ Per-guild sync completed for {synced} guilds")

    # ✅ Global sync (slower, but good for future servers)
    try:
        await bot.tree.sync()
        print("🌍 Global slash commands synced")
    except Exception as e:
        print(f"⚠️ Global sync error: {e}")

    asyncio.create_task(update_presence())
    asyncio.create_task(reset_daily_translations())
    print("Instance is healthy ✅")


@bot.event
async def on_guild_join(guild: discord.Guild):
    try:
        await bot.tree.sync(guild=guild)
        print(f"🆕 Synced commands to NEW guild {guild.name} ({guild.id})")
    except Exception as e:
        print(f"❌ Failed syncing new guild {guild.id}: {e}")

    # Try to apply bot role color if possible
    try:
        bot_role = guild.me.top_role
        await bot_role.edit(color=discord.Color(BOT_COLOR))
    except:
        pass


async def update_presence():
    await bot.wait_until_ready()
    while True:
        try:
            guilds = len(bot.guilds)
            translations = bot.total_translations
            activity = discord.Game(
                name=f"{guilds} servers | {translations} translated"
            )
            await bot.change_presence(activity=activity)
        except Exception as e:
            print(f"⚠️ Presence update failed: {e}")
        await asyncio.sleep(PRESENCE_INTERVAL)


async def reset_daily_translations():
    await bot.wait_until_ready()
    while True:
        now = datetime.utcnow()
        reset_time = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        await asyncio.sleep((reset_time - now).total_seconds())
        bot.total_translations = 0
        print("🔄 Daily translation counter reset")


if __name__ == "__main__":
    bot.run(os.getenv("BOT_TOKEN"))