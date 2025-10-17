import os
import asyncio
import discord
from discord.ext import commands, tasks
from utils import database
from datetime import datetime, timedelta

BOT_COLOR = 0xde002a  # Bot role color
PRESENCE_INTERVAL = 300  # 5 minutes

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.reactions = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# -----------------------------
# Track total translations
# -----------------------------
bot.total_translations = 0

# -----------------------------
# Initialize DB and load cogs
# -----------------------------
async def main():
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
# Sync slash commands
# -----------------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")
    print("Instance is healthy")
    # Start rich presence loop
    if not hasattr(bot, "_presence_task"):
        bot._presence_task = asyncio.create_task(update_presence())
    # Start daily reset loop
    if not hasattr(bot, "_daily_reset_task"):
        bot._daily_reset_task = asyncio.create_task(daily_reset_translations())

# -----------------------------
# Update rich presence every 5 minutes
# -----------------------------
async def update_presence():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            guild_count = len(bot.guilds)
            total_trans = getattr(bot, "total_translations", 0)
            activity = discord.Game(name=f"{guild_count} servers | {total_trans} translations today")
            await bot.change_presence(activity=activity)
        except Exception as e:
            print(f"⚠️ Presence update failed: {e}")
        await asyncio.sleep(PRESENCE_INTERVAL)

# -----------------------------
# Reset daily translation counter at 00:00 UTC
# -----------------------------
async def daily_reset_translations():
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.utcnow()
        next_reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        wait_seconds = (next_reset - now).total_seconds()
        await asyncio.sleep(wait_seconds)
        bot.total_translations = 0
        print("🔄 Daily translations counter reset")

# -----------------------------
# Set bot role color on new guilds
# -----------------------------
@bot.event
async def on_guild_join(guild: discord.Guild):
    bot_member = guild.me or await guild.fetch_member(bot.user.id)
    if not bot_member:
        return
    bot_role = bot_member.top_role
    try:
        await bot_role.edit(color=discord.Color(BOT_COLOR), reason="Set initial bot role color")
        print(f"🎨 Bot role color set automatically in new guild '{guild.name}'")
    except Exception as e:
        print(f"⚠️ Failed to set bot role color in new guild '{guild.name}': {e}")

# -----------------------------
# Test command
# -----------------------------
@bot.tree.command(name="test", description="Test if interactions work")
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("✅ Test command works!", ephemeral=True)

# -----------------------------
# Run bot
# -----------------------------
if __name__ == "__main__":
    asyncio.run(main())
