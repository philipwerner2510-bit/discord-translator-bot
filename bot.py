# bot.py — Zephyra Main Entrypoint

import os
import logging
import discord
from discord.ext import commands
from discord import app_commands

from utils.brand import NAME, COLOR, footer_text
from utils import database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
log = logging.getLogger("zephyra.boot")

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise SystemExit("❌ DISCORD_TOKEN not set!")

# ==========================
# Intents
# ==========================
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.reactions = True
intents.guilds = True
intents.members = True
intents.dm_messages = True
intents.voice_states = True  # ✅ Needed for XP voice rewards

# ==========================
# Bot
# ==========================
class Zephyra(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"/help • By Polarix1954"
            ),
        )

    async def setup_hook(self):
        log.info("🗃 Ensuring database tables exist...")
        await database.ensure_tables()

        EXTENSIONS = [
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
            "cogs.xp_system"
        ]

        for ext in EXTENSIONS:
            try:
                await self.load_extension(ext)
                log.info(f"✅ Loaded {ext}")
            except Exception as e:
                log.error(f"❌ Failed to load {ext}: {e}")

        await self.tree.sync()
        log.info("🪄 Slash command sync complete.")

    async def on_ready(self):
        log.info(f"✅ Logged in as {self.user} ({self.user.id}) — {NAME}")

        guild_count = len(self.guilds)
        total_users = sum(g.member_count for g in self.guilds if g.member_count)

        log.info(f"📊 Connected to {guild_count} servers with ~{total_users:,} users.")
        print("────────────────────────────────────────")

# ==========================
# Run bot
# ==========================
if __name__ == "__main__":
    log.info(f"🔧 Booting {NAME}")
    bot = Zephyra()
    try:
        bot.run(TOKEN)
    except Exception as e:
        log.error(f"❌ Fatal error in bot.run(): {e}")
