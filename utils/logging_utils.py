# utils/logging_utils.py  (UPDATED)
import os, json
import datetime, traceback
from io import BytesIO
import aiofiles
import discord
from typing import Optional
from utils import database

LOG_FILE = os.getenv("BOT_LOG_PATH", "/mnt/data/bot_errors.log")
ALERT_COOLDOWN = 30.0  # seconds
_last_alert: dict[int, float] = {}

async def log_error(
    bot: Optional[discord.Client],
    guild_id: Optional[int],
    message: str,
    exc: Exception | None = None,
    admin_notify: bool = False
):
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)) if exc else None

    line = f"[{timestamp}][Guild {guild_id}] {message}"
    if tb:
        line += f"\nTraceback:\n{tb}"
    print(line)
    try:
        print(json.dumps({"time": timestamp, "guild": guild_id, "message": message}, ensure_ascii=False))
    except Exception:
        pass

    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    except Exception:
        pass
    try:
        async with aiofiles.open(LOG_FILE, "a", encoding="utf-8") as f:
            await f.write(line + "\n")
    except Exception as file_exc:
        print(f"[Logging Error] Could not write to log file: {file_exc}")

    if not (admin_notify and bot and guild_id):
        return

    now = datetime.datetime.utcnow().timestamp()
    if now - _last_alert.get(guild_id, 0.0) < ALERT_COOLDOWN:
        return
    _last_alert[guild_id] = now

    guild = bot.get_guild(guild_id)
    if not guild or not getattr(guild, "me", None):
        return

    ch = None
    try:
        err_ch_id = await database.get_error_channel(guild_id)
        if err_ch_id:
            ch = guild.get_channel(err_ch_id)
    except Exception:
        pass

    candidates = ([ch] if ch else []) + list(guild.text_channels[:10])
    for c in candidates:
        if not c:
            continue
        perms = c.permissions_for(guild.me)
        if not perms.send_messages:
            continue
        try:
            embed = discord.Embed(
                title="⚠️ Bot Error",
                description=message,
                color=0xDE002A,
                timestamp=datetime.datetime.utcnow()
            )
            if tb:
                embed.add_field(name="Traceback", value=f"```py\n{tb[:1024]}```", inline=False)
            if tb and len(tb) > 1000 and perms.attach_files:
                buf = BytesIO(tb.encode("utf-8")); buf.seek(0)
                await c.send(embed=embed, file=discord.File(buf, filename="traceback.txt"))
            else:
                await c.send(embed=embed)
            break
        except Exception as e:
            print(f"[Logging Warning] Could not send log to Discord in #{getattr(c,'name','?')}: {e}")
            continue