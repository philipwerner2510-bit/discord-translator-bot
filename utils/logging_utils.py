import os
import time
import aiofiles
import traceback
import datetime
import discord

LOG_PATH = os.getenv("BOT_LOG_PATH", "/mnt/data/bot_errors.log")

_admin_notify_cache = {}  # guild_id → last_notify_ts
ADMIN_NOTIFY_COOLDOWN = 900  # 15 min


async def log_error(bot, guild_id, message: str, exc: Exception = None, admin_notify=False):
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    base = f"[{timestamp}][Guild {guild_id}] {message}"

    stack = ""
    if exc:
        stack = "".join(traceback.format_exception(exc))[:2000]
        base += f"\n{stack}"

    print(base)

    try:
        async with aiofiles.open(LOG_PATH, "a", encoding="utf-8") as f:
            await f.write(base + "\n")
    except:
        pass

    if not (bot and admin_notify): return

    now = time.time()
    last = _admin_notify_cache.get(guild_id, 0)
    if now - last < ADMIN_NOTIFY_COOLDOWN:
        return
    _admin_notify_cache[guild_id] = now

    guild = bot.get_guild(guild_id)
    if not guild: return

    ch_id = await database.get_error_channel(guild_id)
    ch = guild.get_channel(ch_id) if ch_id else None
    if not ch: return

    try:
        emb = discord.Embed(
            title="⚠️ Bot Error",
            description=message,
            timestamp=datetime.datetime.utcnow(),
            color=0xDE002A
        )
        if stack:
            emb.add_field(name="Details", value=f"```{stack[:1020]}```", inline=False)
        await ch.send(embed=emb)
    except:
        pass