import os
import aiosqlite

DB_PATH = os.getenv("BOT_DB_PATH", "/mnt/data/bot_data.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS user_lang(user_id INTEGER PRIMARY KEY, lang TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS server_lang(guild_id INTEGER PRIMARY KEY, lang TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS translation_channels(guild_id INTEGER PRIMARY KEY, channels TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS error_channel(guild_id INTEGER PRIMARY KEY, channel_id INTEGER)")
        await db.execute("CREATE TABLE IF NOT EXISTS bot_emote(guild_id INTEGER PRIMARY KEY, emote TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS user_translations(user_id INTEGER PRIMARY KEY, count INTEGER DEFAULT 0)")
        await db.execute("CREATE TABLE IF NOT EXISTS guild_translations(guild_id INTEGER PRIMARY KEY, count INTEGER DEFAULT 0)")
        await db.commit()

async def export_db(target):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.backup(target)

# 🔹 Language settings
async def set_user_lang(uid, lang):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO user_lang(user_id,lang) VALUES(?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET lang=excluded.lang", (uid, lang)
        )
        await db.commit()

async def get_user_lang(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        row = await db.execute_fetchone(
            "SELECT lang FROM user_lang WHERE user_id=?", (uid,))
        return row[0] if row else None

async def set_server_lang(gid, lang):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO server_lang(guild_id,lang) VALUES(?,?) "
            "ON CONFLICT(guild_id) DO UPDATE SET lang=excluded.lang", (gid, lang)
        )
        await db.commit()

async def get_server_lang(gid):
    async with aiosqlite.connect(DB_PATH) as db:
        row = await db.execute_fetchone(
            "SELECT lang FROM server_lang WHERE guild_id=?", (gid,))
        return row[0] if row else None

async def set_translation_channels(gid, lst):
    s = ",".join(map(str, lst))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO translation_channels VALUES(?,?) "
            "ON CONFLICT(guild_id) DO UPDATE SET channels=excluded.channels", (gid, s)
        )
        await db.commit()

async def get_translation_channels(gid):
    async with aiosqlite.connect(DB_PATH) as db:
        row = await db.execute_fetchone(
            "SELECT channels FROM translation_channels WHERE guild_id=?", (gid,))
        return [int(x) for x in row[0].split(",")] if (row and row[0]) else []

async def set_error_channel(gid, cid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO error_channel VALUES(?,?) "
            "ON CONFLICT(guild_id) DO UPDATE SET channel_id=excluded.channel_id", (gid, cid)
        )
        await db.commit()

async def get_error_channel(gid):
    async with aiosqlite.connect(DB_PATH) as db:
        row = await db.execute_fetchone(
            "SELECT channel_id FROM error_channel WHERE guild_id=?", (gid,))
        return row[0] if row else None

async def set_bot_emote(gid, emote):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO bot_emote VALUES(?,?) "
            "ON CONFLICT(guild_id) DO UPDATE SET emote=excluded.emote", (gid, emote)
        )
        await db.commit()

async def get_bot_emote(gid):
    async with aiosqlite.connect(DB_PATH) as db:
        row = await db.execute_fetchone(
            "SELECT emote FROM bot_emote WHERE guild_id=?", (gid,))
        return row[0] if row else None

# 🔹 Analytics counters
async def increment_user_counter(uid, amt):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO user_translations(user_id,count) VALUES(?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET count=count+?",
            (uid, amt, amt)
        )
        await db.commit()

async def increment_guild_counter(gid, amt):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO guild_translations(guild_id,count) VALUES(?,?) "
            "ON CONFLICT(guild_id) DO UPDATE SET count=count+?",
            (gid, amt, amt)
        )
        await db.commit()

async def get_user_count(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        row = await db.execute_fetchone(
            "SELECT count FROM user_translations WHERE user_id=?", (uid,))
        return row[0] if row else 0

async def get_guild_count(gid):
    async with aiosqlite.connect(DB_PATH) as db:
        row = await db.execute_fetchone(
            "SELECT count FROM guild_translations WHERE guild_id=?", (gid,))
        return row[0] if row else 0

async def get_top_users(n):
    async with aiosqlite.connect(DB_PATH) as db:
        return await db.execute_fetchall(
            "SELECT user_id,count FROM user_translations ORDER BY count DESC LIMIT ?", (n,))