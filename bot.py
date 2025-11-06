# bot.py
import os
import logging
import asyncio
import discord
from discord.ext import commands

from utils.brand import NAME, COLOR
from utils import database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
log = logging.getLogger("zephyra.boot")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.messages = True
INTENTS.reactions = True
INTENTS.guilds = True
INTENTS.members = True  # for better caching on profiles/leaderboard

bot = commands.Bot(command_prefix="!", intents=INTENTS)

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
    "cogs.xp_system",
]

@bot.event
async def on_ready():
    log.info("✅ Logged in as %s (%s) — %s", bot.user, bot.user.id, NAME)
    try:
        synced = await bot.tree.sync()
        log.info("🪄 Slash command sync complete. %d commands registered.", len(synced))
    except Exception as e:
        log.exception("Slash sync failed: %s", e)

async def load_cogs():
    for ext in COGS:
        try:
            await bot.load_extension(ext)
            log.info("✅ Loaded %s", ext)
        except Exception as e:
            log.error("❌ Failed to load %s: %r", ext, e)

async def main():
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN not set!")
        raise SystemExit(1)

    log.info("🔧 Booting %s", NAME)

    # Ensure DB schema (supports both names)
    try:
        if hasattr(database, "ensure_tables"):
            await database.ensure_tables()
        else:
            await database.ensure_schema()
        log.info("🗃 Ensuring database tables exist...")
    except Exception as e:
        log.error("❌ Fatal error preparing database: %s", e)
        raise

    await load_cogs()

    # Presence
    try:
        await bot.change_presence(activity=discord.Game(name=f"{NAME} is online"))
    except Exception:
        pass

    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except SystemExit:
        pass
    except Exception as e:
        log.error("❌ Fatal error in bot.run(): %s", e)
