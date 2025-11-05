import os
import asyncio
import discord
from discord.ext import commands
from utils import database
from utils.brand import COLOR, EMOJI_PRIMARY, EMOJI_THINKING, EMOJI_HIGHLIGHT, EMOJI_ACCENT, footer, PRESENCE_TEMPLATE

PRESENCE_INTERVAL = 40  # seconds

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.reactions = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

bot.total_translations = 0
bot.start_time = None

async def main():
    await database.init_db()
    async with bot:
        for ext in [
            "cogs.user_commands",
            "cogs.admin_commands",
            "cogs.translate",
            "cogs.events",
            "cogs.ops_commands",
            "cogs.analytics_commands",
            "cogs.welcome",
            "cogs.invite_command",
            "cogs.owner_commands",
            "cogs.context_menu",
        ]:
            try:
                await bot.load_extension(ext)
                print(f"✅ Loaded {ext}")
            except Exception as e:
                print(f"❌ Failed to load {ext}: {e}")
        await bot.start(os.environ["BOT_TOKEN"])

@bot.event
async def on_ready():
    bot.start_time = discord.utils.utcnow()
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")
    if not hasattr(bot, "_presence_task"):
        bot._presence_task = asyncio.create_task(update_presence())

async def update_presence():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            servers = len(bot.guilds)
            today, total = await database.get_translation_totals()
            lines = [
                PRESENCE_TEMPLATE.format(servers=servers, translations=today),
                f"{EMOJI_HIGHLIGHT} {today} translations today",
                f"{EMOJI_ACCENT} Assisting {servers} servers",
                f"{EMOJI_THINKING} Ready to help",
            ]
            for text in lines:
                await bot.change_presence(activity=discord.Game(name=text))
                await asyncio.sleep(PRESENCE_INTERVAL)
        except Exception as e:
            print(f"[presence] error: {e}")
            await asyncio.sleep(PRESENCE_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())