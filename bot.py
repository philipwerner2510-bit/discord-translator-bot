# bot.py
import os
import asyncio
import traceback
import discord
from discord.ext import commands
from utils.brand import COLOR as BOT_COLOR, PRESENCE_TEMPLATE, NAME as BOT_NAME
from utils import database

PRESENCE_INTERVAL = 300  # seconds

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.reactions = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# runtime counters
bot.total_translations = 0
bot.libre_translations = 0
bot.ai_translations = 0
bot.cache_hits = 0
bot.cache_misses = 0
bot.cached_translations = 0

EXTENSIONS = [
    "cogs.user_commands",
    "cogs.admin_commands",
    "cogs.translate",
    "cogs.events",
    "cogs.ops_commands",
    "cogs.analytics_commands",
    "cogs.welcome",
    "cogs.invite_command",
    "cogs.owner_commands",
]

async def presence_loop():
    """Update presence every PRESENCE_INTERVAL seconds."""
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            guild_count = len(bot.guilds)
            total_trans = getattr(bot, "total_translations", 0)
            activity = discord.Game(
                name=PRESENCE_TEMPLATE.format(servers=guild_count, translations=total_trans)
            )
            await bot.change_presence(activity=activity)
        except Exception as e:
            print(f"⚠️ Presence update failed: {e}")
        await asyncio.sleep(PRESENCE_INTERVAL)

@bot.event
async def on_ready():
    # sync global commands (per-guild sync is not needed unless you target specific guilds)
    try:
        await bot.tree.sync()
        print("🌍 Global slash commands synced")
    except Exception as e:
        print(f"❌ Global sync failed: {type(e).__name__}: {e}")
        traceback.print_exc()

    print(f"✅ Logged in as {bot.user} ({bot.user.id}) — {BOT_NAME}")

    # start presence loop once
    if not hasattr(bot, "_presence_task"):
        bot._presence_task = asyncio.create_task(presence_loop())

@bot.event
async def on_guild_join(guild: discord.Guild):
    """
    Best-effort: tint our top role to the brand color.
    Only if we have Manage Roles and the role is editable.
    Stay silent if we can't.
    """
    try:
        me = guild.me or await guild.fetch_member(bot.user.id)
        if not me:
            return

        # Need Manage Roles permission
        perms = me.guild_permissions
        if not perms.manage_roles:
            return

        role = me.top_role
        # Skip if role is managed/default or not editable due to hierarchy
        if role.is_default() or role.managed:
            return

        await role.edit(color=discord.Color(BOT_COLOR), reason=f"Set {BOT_NAME} brand color")
    except discord.Forbidden:
        # Missing permission or hierarchy issue — ignore quietly
        pass
    except Exception as e:
        # Log unexpected errors only
        print(f"⚠️ Could not tint role in {guild.name}: {e}")

async def main():
    # init DB (creates tables if missing)
    await database.init_db()

    # load cogs
    async with bot:
        for ext in EXTENSIONS:
            try:
                await bot.load_extension(ext)
                print(f"✅ Loaded {ext}")
            except Exception as e:
                print(f"❌ Failed to load {ext}: {e}")

        token = os.environ["BOT_TOKEN"]
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
