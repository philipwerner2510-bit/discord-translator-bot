import os
import discord
from discord.ext import commands

# Get the token directly from environment variables
TOKEN = os.environ["BOT_TOKEN"]

# Intents
intents = discord.Intents.default()
intents.messages = True
intents.reactions = True
intents.message_content = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# List of cogs to load
initial_extensions = [
    "cogs.admin_commands",
    "cogs.user_commands",
    "cogs.translate",
    "cogs.events"
]

# Event: Bot ready
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

# Load cogs/extensions
if __name__ == "__main__":
    for ext in initial_extensions:
        bot.load_extension(ext)

    bot.run(TOKEN)
