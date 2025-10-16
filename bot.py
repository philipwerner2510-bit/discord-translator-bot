import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.messages = True
intents.reactions = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Load cogs
initial_extensions = [
    "cogs.admin_commands",
    "cogs.user_commands",
    "cogs.translate",
    "cogs.events"
]

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

if __name__ == "__main__":
    for ext in initial_extensions:
        bot.load_extension(ext)
    bot.run(TOKEN)
