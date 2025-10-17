import os
import asyncio
import discord
from discord.ext import commands
from utils import database

BOT_COLOR = 0xde002a  # Bot role color

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.reactions = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot.total_translations = 0  # Initialize real-time translation counter

# -----------------------------
# Background task for rich presence
# -----------------------------
async def update_presence():
    while True:
        try:
            # Show number of servers
            await bot.change_presence(activity=discord.Game(name=f"on {len(bot.guilds)} servers | a silly bot"))
            await asyncio.sleep(300)

            # Show total translations today
            await bot.change_presence(activity=discord.Game(name=f"{getattr(bot, 'total_translations', 0)} translations today | a silly bot"))
            await asyncio.sleep(300)

        except Exception as e:
            print(f"⚠️ Presence update failed: {e}")
            await asyncio.sleep(60)

# -----------------------------
# Load cogs
# -----------------------------
async def load_cogs():
    for ext in ["cogs.user_commands", "cogs.admin_commands", "cogs.translate", "cogs.events"]:
        try:
            await bot.load_extension(ext)
            print(f"✅ Loaded {ext}")
        except Exception as e:
            print(f"❌ Failed to load {ext}: {e}")

# -----------------------------
# Setup hook
# -----------------------------
async def setup_hook_override():
    await load_cogs()

bot.setup_hook = setup_hook_override

# -----------------------------
# Ready event
# -----------------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")
    print("Instance is healthy")

    # Start presence updater once
    if not hasattr(bot, "_presence_task"):
        bot._presence_task = asyncio.create_task(update_presence())

    # Set bot role color
    for guild in bot.guilds:
        bot_member = guild.me or await guild.fetch_member(bot.user.id)
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
    # Initialize DB first
    asyncio.run(database.init_db())
    # Start bot
    asyncio.run(bot.start(os.environ["BOT_TOKEN"]))
