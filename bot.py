# bot.py  (UPDATED)
import os
import asyncio
import discord
from discord.ext import commands
from datetime import datetime, timedelta

from utils import database
from utils.logging_utils import log_error

BOT_COLOR = 0xDE002A
PRESENCE_INTERVAL = 300  # 5 minutes

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.reactions = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot.total_translations = 0

# expose logging to cogs
async def _log(gid: int | None, msg: str, exc: Exception | None = None, notify: bool = False):
    await log_error(bot, gid, msg, exc, admin_notify=notify)
bot.log_error = _log  # type: ignore[attr-defined]

async def _presence_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            activity = discord.Game(name=f"{len(bot.guilds)} servers | {getattr(bot,'total_translations',0)} translations today")
            await bot.change_presence(activity=activity)
        except Exception as e:
            await bot.log_error(None, "Presence update failed", e)
        await asyncio.sleep(PRESENCE_INTERVAL)

async def _midnight_reset_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.utcnow()
        next_reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        await asyncio.sleep(max(1.0, (next_reset - now).total_seconds()))
        bot.total_translations = 0
        print("🔄 Daily translations counter reset")

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")
    print("Instance is healthy")
    if not hasattr(bot, "_presence_task") or bot._presence_task.done():
        bot._presence_task = asyncio.create_task(_presence_loop())
    if not hasattr(bot, "_midnight_task") or bot._midnight_task.done():
        bot._midnight_task = asyncio.create_task(_midnight_reset_loop())

class MyBot(commands.Bot):
    async def setup_hook(self) -> None:
        await database.init_db()
        for ext in ("cogs.user_commands", "cogs.admin_commands", "cogs.translate", "cogs.events"):
            try:
                await bot.load_extension(ext)
                print(f"✅ Loaded {ext}")
            except Exception as e:
                await bot.log_error(None, f"Failed to load {ext}", e, notify=True)
        try:
            await bot.tree.sync()  # global sync; for fast dev use guild sync instead
            print("✅ Slash commands synced")
        except Exception as e:
            await bot.log_error(None, "Slash command sync failed", e, notify=True)

bot.__class__ = MyBot  # swap class to use setup_hook()

@bot.event
async def on_guild_join(guild: discord.Guild):
    me = guild.me or await guild.fetch_member(bot.user.id)
    if not me:
        return
    role = me.top_role
    if not role or role.managed:
        return
    try:
        await role.edit(color=discord.Color(BOT_COLOR), reason="Set initial bot role color")
        print(f"🎨 Set bot role color in '{guild.name}'")
    except discord.Forbidden:
        pass
    except Exception as e:
        await bot.log_error(guild.id, "Failed to set bot role color", e)

@bot.tree.command(name="test", description="Test if interactions work")
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("✅ Test command works!", ephemeral=True)

async def amain():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Missing BOT_TOKEN environment variable.")
    async with bot:
        await bot.start(token)

if __name__ == "__main__":
    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        pass