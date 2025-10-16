import os
import asyncio
import discord
from discord.ext import commands

# -----------------------------
# Bot setup
# -----------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.reactions = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# List of your cogs
initial_extensions = [
    "cogs.user_commands",
    "cogs.admin_commands",
    "cogs.translate"
]

# -----------------------------
# Async main for proper cog loading
# -----------------------------
async def main():
    async with bot:
        # Load all cogs
        for ext in initial_extensions:
            try:
                await bot.load_extension(ext)
                print(f"✅ Loaded {ext}")
            except Exception as e:
                print(f"❌ Failed to load {ext}: {e}")
        
        # Start the bot
        await bot.start(os.environ["BOT_TOKEN"])

# -----------------------------
# on_ready event for syncing commands
# -----------------------------
@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"✅ Synced {len(synced)} commands")
    print(f"✅ Logged in as {bot.user}")

# -----------------------------
# Minimal test command
# -----------------------------
@bot.tree.command(name="test", description="Test if interactions work")
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("✅ Test command works!", ephemeral=True)

# -----------------------------
# Run bot
# -----------------------------
if __name__ == "__main__":
    asyncio.run(main()) 
