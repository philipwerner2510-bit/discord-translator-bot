import os
import asyncio
import discord
from discord.ext import commands
from utils import database
import itertools
import datetime

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.reactions = True
intents.guilds = True
intents.dm_messages = True

# -----------------------------
# Custom Bot class with setup_hook
# -----------------------------
class MyBot(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.translations_today = 0  # global counter

    async def setup_hook(self):
        # Schedule background tasks safely
        self.loop.create_task(update_presence(self))
        self.loop.create_task(reset_daily_translations(self))

bot = MyBot(command_prefix="!", intents=intents)

# -----------------------------
# Background Tasks
# -----------------------------
async def update_presence(bot):
    await bot.wait_until_ready()
    activity_cycle = itertools.cycle(["servers", "translations"])
    while not bot.is_closed():
        try:
            next_display = next(activity_cycle)
            if next_display == "servers":
                server_count = len(bot.guilds)
                activity = discord.Game(name=f"Playing a silly bot 🎲 | {server_count} servers")
            else:
                translations = getattr(bot, "translations_today", 0)
                activity = discord.Game(name=f"Playing a silly bot 🎲 | {translations} translations today")
            await bot.change_presence(activity=activity)
            await asyncio.sleep(300)  # switch every 5 minutes
        except Exception as e:
            print(f"Failed to update presence: {e}")
            await asyncio.sleep(60)

async def reset_daily_translations(bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.datetime.utcnow()
        next_midnight = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        seconds_until_midnight = (next_midnight - now).total_seconds()
        await asyncio.sleep(seconds_until_midnight)
        bot.translations_today = 0
        print("✅ Reset translations_today counter for new UTC day")

# -----------------------------
# Load all cogs async
# -----------------------------
async def main():
    # Initialize database
    await database.init_db()

    async with bot:
        for ext in ["cogs.user_commands", "cogs.admin_commands", "cogs.translate", "cogs.events"]:
            try:
                await bot.load_extension(ext)
                print(f"✅ Loaded {ext}")
            except Exception as e:
                print(f"❌ Failed to load {ext}: {e}")
        await bot.start(os.environ["BOT_TOKEN"])

# -----------------------------
# Ready event
# -----------------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")
    print("Instance is healthy")

# -----------------------------
# Test command
# -----------------------------
@bot.tree.command(name="test", description="Test if interactions work")
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("✅ Test command works!", ephemeral=True)

if __name__ == "__main__":
    asyncio.run(main())
