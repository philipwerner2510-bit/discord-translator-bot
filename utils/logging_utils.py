# utils/logging_utils.py
import datetime, traceback
import aiofiles
import discord
from utils import database

LOG_FILE = "bot_errors.log"

async def log_error(bot, guild_id, message: str, exc: Exception = None, admin_notify=False):
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}][Guild {guild_id}] {message}"
    tb = None
    if exc:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        log_msg += f"\nTraceback:\n{tb}"
    print(log_msg)
    try:
        async with aiofiles.open(LOG_FILE, "a", encoding="utf-8") as f:
            await f.write(log_msg + "\n")
    except Exception as file_exc:
        print(f"[Logging Error] Could not write to log file: {file_exc}")

    if admin_notify and bot and guild_id:
        try:
            ch_id = await database.get_error_channel(guild_id)
            if ch_id:
                guild = bot.get_guild(guild_id)
                if guild:
                    ch = guild.get_channel(ch_id)
                    if ch:
                        embed = discord.Embed(title="Error", description=message, color=0xE74C3C)
                        if tb:
                            embed.add_field(name="Traceback", value=f"```py\n{tb[:1000]}```", inline=False)
                        await ch.send(embed=embed)
        except Exception as e:
            print(f"[Logging Warning] Could not notify admin channel: {e}")
