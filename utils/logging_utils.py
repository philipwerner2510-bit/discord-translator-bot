import datetime
import traceback
import aiofiles
import discord

LOG_FILE = "bot_errors.log"

async def log_error(bot, guild_id, message: str, exc: Exception = None, admin_notify=False):
    """
    Logs an error message with optional exception traceback.
    Sends logs to console, async file, and optionally notifies a Discord channel.
    
    Parameters:
    - bot: discord.Bot instance (or None if unavailable)
    - guild_id: Discord guild/server ID
    - message: Short description of the error/event
    - exc: Optional exception object
    - admin_notify: If True, sends an embed to first available text channel
    """
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}][Guild {guild_id}] {message}"

    if exc:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        log_msg += f"\nTraceback:\n{tb}"

    # 1️⃣ Console logging
    print(log_msg)

    # 2️⃣ Async file logging
    try:
        async with aiofiles.open(LOG_FILE, "a", encoding="utf-8") as f:
            await f.write(log_msg + "\n")
    except Exception as file_exc:
        print(f"[Logging Error] Could not write to log file: {file_exc}")

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
                            # Embed field limited to 1024 characters
                            embed.add_field(
                                name="Traceback",
                                value=f"```py\n{tb[:1024]}```",
                                inline=False
                            )
                        await ch.send(embed=embed)
                        break  # send to first available channel
                    except Exception as discord_exc:
                        print(f"[Logging Warning] Could not send log to Discord: {discord_exc}")
