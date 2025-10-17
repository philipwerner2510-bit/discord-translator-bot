import datetime
import traceback
import aiofiles
import discord

LOG_FILE = "bot_errors.log"

async def log_error(bot, guild_id, message: str, exc: Exception = None, admin_notify=False):
    """
    Logs an error message with optional exception traceback.
    Sends to console, file, and optionally a server admin channel.
    """
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}][Guild {guild_id}] {message}"

    if exc:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        log_msg += f"\nTraceback:\n{tb}"

    # 1️⃣ Console
    print(log_msg)

    # 2️⃣ File logging (async-safe)
    async with aiofiles.open(LOG_FILE, "a", encoding="utf-8") as f:
        await f.write(log_msg + "\n")

    # 3️⃣ Discord admin notification
    if admin_notify and bot:
        guild = bot.get_guild(guild_id)
        if guild:
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    try:
                        embed = discord.Embed(
                            title="⚠️ Bot Error",
                            description=message,
                            color=0xde002a,
                            timestamp=datetime.datetime.utcnow()
                        )
                        if exc:
                            embed.add_field(
                                name="Traceback",
                                value=f"```py\n{tb[:1024]}```",  # limit to first 1024 chars
                                inline=False
                            )
                        await ch.send(embed=embed)
                        break  # send to the first channel bot can post
                    except:
                        continue
