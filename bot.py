import os
import asyncio
import discord
from discord.ext import commands
from utils.database import init_db  # directly import init_db

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.reactions = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# -----------------------------
# Load all cogs async
# -----------------------------
async def main():
    # Initialize the database first
    await init_db()

    async with bot:
        for ext in ["cogs.user_commands", "cogs.admin_commands", "cogs.translate", "cogs.events"]:
            try:
                await bot.load_extension(ext)
                print(f"✅ Loaded {ext}")
            except Exception as e:
                print(f"❌ Failed to load {ext}: {e}")

        await bot.start(os.environ["BOT_TOKEN"])

# -----------------------------
# Sync all slash commands on ready
# -----------------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")

# -----------------------------
# Test command
# -----------------------------
@bot.tree.command(name="test", description="Test if interactions work")
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("✅ Test command works!", ephemeral=True)

if __name__ == "__main__":
    asyncio.run(main())
