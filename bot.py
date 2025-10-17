import os
import asyncio
import discord
from discord.ext import commands, tasks
from utils import database

BOT_COLOR = 0xde002a  # Hex color for bot role

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
async def load_cogs():
    for ext in ["cogs.user_commands", "cogs.admin_commands", "cogs.translate", "cogs.events"]:
        try:
            await bot.load_extension(ext)
            print(f"✅ Loaded {ext}")
        except Exception as e:
            print(f"❌ Failed to load {ext}: {e}")

# -----------------------------
# Presence updater
# -----------------------------
async def update_presence():
    while True:
        try:
            # Number of servers
            await bot.change_presence(activity=discord.Game(name=f"on {len(bot.guilds)} servers | a silly bot"))
            await asyncio.sleep(300)

            # Total translations today (dummy example, replace with DB count if tracking)
            # For now we'll simulate with 0
            total_translations = 0
            await bot.change_presence(activity=discord.Game(name=f"{total_translations} translations today | a silly bot"))
            await asyncio.sleep(300)
        except Exception as e:
            print(f"⚠️ Presence update failed: {e}")
            await asyncio.sleep(60)

# -----------------------------
# Main async startup
# -----------------------------
async def main():
    await database.init_db()
    await load_cogs()

    # Start presence updater
    bot.loop.create_task(update_presence())

    await bot.start(os.environ["BOT_TOKEN"])

# -----------------------------
# Ready event
# -----------------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")
    print("Instance is healthy")

    # Set bot role color in all guilds
    for guild in bot.guilds:
        bot_member = guild.me
        if bot_member:
            top_role = bot_member.top_role
            if top_role.color.value != BOT_COLOR:
                try:
                    await top_role.edit(color=discord.Color(BOT_COLOR), reason="Set bot role color")
                    print(f"🎨 Set bot role color in guild '{guild.name}'")
                except Exception as e:
                    print(f"⚠️ Failed to set bot role color in '{guild.name}': {e}")

# -----------------------------
# Test command
# -----------------------------
@bot.tree.command(name="test", description="Test if interactions work")
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("✅ Test command works!", ephemeral=True)

# -----------------------------
# Run the bot
# -----------------------------
if __name__ == "__main__":
    asyncio.run(main())
