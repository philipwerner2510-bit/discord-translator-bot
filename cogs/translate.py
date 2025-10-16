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
# Sync commands after cogs
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

# -----------------------------
# Main async loader
# -----------------------------
async def main():
    # Initialize database first
    await database.init_db()

    async with bot:
        for ext in ["cogs.user_commands", "cogs.admin_commands", "cogs.translate"]:
            try:
                await bot.load_extension(ext)
                print(f"✅ Loaded {ext}")
            except Exception as e:
                print(f"❌ Failed to load {ext}: {e}")

        await bot.start(os.environ["BOT_TOKEN"])

if __name__ == "__main__":
    asyncio.run(main()) 
