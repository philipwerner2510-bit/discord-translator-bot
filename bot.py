import os
import asyncio
import discord
from discord.ext import commands
from utils import database

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.reactions = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# -----------------------------
# Global counters
# -----------------------------
bot.translations_today = 0  # total translations sent today

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
# Rich Presence
# -----------------------------
import itertools

async def update_presence():
    await bot.wait_until_ready()
    activity_cycle = itertools.cycle(["servers", "translations"])  # alternate

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

bot.loop.create_task(update_presence())

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
