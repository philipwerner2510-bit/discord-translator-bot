async def log_error(bot, guild_id, message: str):
    guild = bot.get_guild(guild_id)
    if guild:
        print(f"[Guild {guild_id}] {message}")
    else:
        print(f"[Error][Guild {guild_id}] {message}")
