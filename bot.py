import os
import sys
import asyncio
import signal
import logging
from datetime import datetime

import discord
from discord.ext import commands, tasks

# --- Branding (safe imports; won't crash if aliasing changed)
try:
    from utils.brand import NAME, PRIMARY as COLOR, FOOTER_DEV
except Exception:
    NAME = "Zephyra"
    COLOR = 0x00E6F6
    FOOTER_DEV = "Zephyra — Developed by Polarix1954"

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN") or os.getenv("BOT_TOKEN")

# ---- Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("zephyra.boot")

# ---- Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.reactions = True

# ---- Bot
bot = commands.Bot(command_prefix="!", intents=intents)

EXTS = [
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

_synced_once = False  # one-time global sync guard

@bot.event
async def on_ready():
    global _synced_once
    log.info("✅ Logged in as %s (%s) — %s", bot.user, bot.user.id, NAME)

    # One-time global sync so new/changed commands appear even if /ops sync isn't available yet
    if not _synced_once:
        try:
            synced = await bot.tree.sync()
            log.info("🪄 Slash command sync complete. %d commands registered.", len(synced))
        except Exception as e:
            log.error("❌ Slash command sync failed: %r", e)
        else:
            _synced_once = True

    # Start rotating presence
    if not rotate_presence.is_running():
        rotate_presence.start()

@tasks.loop(seconds=60)
async def rotate_presence():
    # Cycle neat, readable activities
    total = getattr(bot, "total_translations", 0)
    choices = [
        discord.Activity(type=discord.ActivityType.watching, name="your messages 🌬️"),
        discord.Activity(type=discord.ActivityType.playing, name="with languages"),
        discord.Activity(type=discord.ActivityType.watching, name=f"{total} translations"),
    ]
    idx = int(datetime.utcnow().timestamp() // 60) % len(choices)
    try:
        await bot.change_presence(activity=choices[idx], status=discord.Status.online)
    except Exception:
        pass

async def load_extensions():
    for ext in EXTS:
        try:
            await bot.load_extension(ext)
            log.info("✅ Loaded %s", ext)
        except commands.errors.ExtensionAlreadyLoaded:
            log.info("↻ Already loaded %s", ext)
        except Exception as e:
            log.error("❌ Failed to load %s: %r", ext, e)

# Graceful shutdown signal support
_stop_event = asyncio.Event()

def _handle_signal(sig, frame):
    log.warning("⚠️  Received signal %s — shutting down…", sig)
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_shutdown())
    except Exception:
        pass

async def _shutdown():
    try:
        await bot.close()
    finally:
        _stop_event.set()

async def _stay_alive():
    # Safety task so the process never exits with code 0 unexpectedly
    while not _stop_event.is_set():
        await asyncio.sleep(3600)

async def main():
    log.info("🔧 Booting Zephyra at %s", datetime.utcnow().isoformat() + "Z")
    log.info("Config: NAME=%s COLOR=0x%06X", NAME, COLOR)

    # Token guard: don't exit, just wait & log
    if not TOKEN:
        log.error("❌ DISCORD_TOKEN/TOKEN/BOT_TOKEN is missing. Waiting instead of exiting.")
        log.error("   Set an env var named DISCORD_TOKEN in Koyeb.")
        await _stay_alive()
        return

    # Load cogs
    await load_extensions()

    # Start bot and also keep a watchdog alive
    runner = asyncio.create_task(bot.start(TOKEN))
    keeper = asyncio.create_task(_stay_alive())

    done, pending = await asyncio.wait(
        {runner, keeper}, return_when=asyncio.FIRST_COMPLETED
    )

    # If bot task returned, log why
    if runner in done:
        try:
            exc = runner.exception()
        except asyncio.CancelledError:
            exc = None
        if exc:
            log.error("💥 bot.start() ended with exception: %r", exc)
        else:
            log.warning("ℹ️ bot.start() returned cleanly — this usually means a logout/close.")
    else:
        log.info("Keeper finished first (shutdown requested).")

    for task in pending:
        task.cancel()

if __name__ == "__main__":
    # Register signal handlers (Koyeb sends SIGTERM on redeploy/stop)
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, _handle_signal)
        except Exception:
            pass

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except SystemExit as e:
        logging.getLogger("zephyra.boot").error("SystemExit(%s) intercepted; keeping process alive.", e.code)
        try:
            asyncio.run(_stay_alive())
        except Exception:
            pass
