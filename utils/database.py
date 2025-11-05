# utils/database.py
import aiosqlite
import os
from datetime import datetime

DB_PATH = os.getenv("BOT_DB_PATH", "/mnt/data/bot_data.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS user_lang(
            user_id INTEGER PRIMARY KEY, lang TEXT)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS server_lang(
            guild_id INTEGER PRIMARY KEY, lang TEXT)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS translation_channels(
            guild_id INTEGER PRIMARY KEY, channels TEXT)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS error_channel(
            guild_id INTEGER PRIMARY KEY, channel_id INTEGER)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS bot_emote(
            guild_id INTEGER PRIMARY KEY, emote TEXT)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS ai_toggle(
            guild_id INTEGER PRIMARY KEY, enabled INTEGER DEFAULT 1)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS user_counts(
            guild_id INTEGER, user_id INTEGER, count INTEGER DEFAULT 0,
            PRIMARY KEY (guild_id, user_id))""")
        await db.execute("""CREATE TABLE IF NOT EXISTS ai_usage(
            month TEXT PRIMARY KEY, tokens INTEGER DEFAULT 0, eur REAL DEFAULT 0.0)""")
        await db.commit()

def _month_key():
    now = datetime.utcnow()
    return f"{now.year:04d}-{now.month:02d}"

# user lang
async def set_user_lang(user_id: int, lang: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""INSERT INTO user_lang(user_id, lang) VALUES(?,?)
            ON CONFLICT(user_id) DO UPDATE SET lang=excluded.lang""", (user_id, lang))
        await db.commit()

async def get_user_lang(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT lang FROM user_lang WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone(); return row[0] if row else None

# server lang
async def set_server_lang(guild_id: int, lang: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""INSERT INTO server_lang(guild_id, lang) VALUES(?,?)
            ON CONFLICT(guild_id) DO UPDATE SET lang=excluded.lang""", (guild_id, lang))
        await db.commit()

async def get_server_lang(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT lang FROM server_lang WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone(); return row[0] if row else None

# channels
async def set_translation_channels(gid: int, channels: list[int]):
    s = ",".join(map(str, channels))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""INSERT INTO translation_channels(guild_id, channels) VALUES(?,?)
            ON CONFLICT(guild_id) DO UPDATE SET channels=excluded.channels""", (gid, s))
        await db.commit()

async def get_translation_channels(gid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT channels FROM translation_channels WHERE guild_id=?", (gid,)) as cur:
            row = await cur.fetchone()
            if row and row[0]:
                return [int(x) for x in row[0].split(",") if x]
            return []

# error ch
async def set_error_channel(gid: int, cid: int|None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""INSERT INTO error_channel(guild_id, channel_id) VALUES(?,?)
            ON CONFLICT(guild_id) DO UPDATE SET channel_id=excluded.channel_id""", (gid, cid))
        await db.commit()

async def get_error_channel(gid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT channel_id FROM error_channel WHERE guild_id=?", (gid,)) as cur:
            row = await cur.fetchone(); return row[0] if row else None

# emote
async def set_bot_emote(gid: int, emote: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""INSERT INTO bot_emote(guild_id, emote) VALUES(?,?)
            ON CONFLICT(guild_id) DO UPDATE SET emote=excluded.emote""", (gid, emote))
        await db.commit()

async def get_bot_emote(gid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT emote FROM bot_emote WHERE guild_id=?", (gid,)) as cur:
            row = await cur.fetchone(); return row[0] if row else None

# ai toggle
async def set_ai_enabled(gid: int, enabled: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""INSERT INTO ai_toggle(guild_id, enabled) VALUES(?,?)
            ON CONFLICT(guild_id) DO UPDATE SET enabled=excluded.enabled""", (gid, 1 if enabled else 0))
        await db.commit()

async def get_ai_enabled(gid: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT enabled FROM ai_toggle WHERE guild_id=?", (gid,)) as cur:
            row = await cur.fetchone(); return bool(row[0]) if row else True

# user counts per guild
async def inc_user_translation(uid: int, gid: int|None=None):
    # if gid unknown, you can pass None; skip
    if gid is None:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""INSERT INTO user_counts(guild_id, user_id, count) VALUES(?,?,1)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET count=count+1""", (gid, uid))
        await db.commit()

async def get_guild_leaderboard(gid: int, limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""SELECT user_id, count FROM user_counts
            WHERE guild_id=? ORDER BY count DESC LIMIT ?""", (gid, limit)) as cur:
            return await cur.fetchall()

# ai usage accounting
async def add_ai_usage(tokens: int, eur: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""INSERT INTO ai_usage(month, tokens, eur) VALUES(?,?,?)
            ON CONFLICT(month) DO UPDATE SET
            tokens = tokens + excluded.tokens,
            eur = eur + excluded.eur
        """, (_month_key(), tokens, eur))
        await db.commit()

async def get_current_ai_usage():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT tokens, eur FROM ai_usage WHERE month=?", (_month_key(),)) as cur:
            row = await cur.fetchone()
            return (row[0], row[1]) if row else (0, 0.0)
