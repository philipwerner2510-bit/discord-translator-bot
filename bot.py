import os
import asyncio
import discord
from discord.ext import commands
from utils import database

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")

async def main():
    # Create DB tables at startup
    await database.init_db()

    # Load cogs
    for ext in ["cogs.user_commands", "cogs.admin_commands", "cogs.translate"]:
        try:
            await bot.load_extension(ext)
            print(f"✅ Loaded {ext}")
        except Exception as e:
            print(f"❌ Failed to load {ext}: {e}")

    await bot.start(os.environ["BOT_TOKEN"])

if __name__ == "__main__":
    asyncio.run(main())
