import aiosqlite
import os
import json
import time

DB_PATH = os.getenv("BOT_DB_PATH", "/mnt/data/bot_data.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_lang(
            user_id INTEGER PRIMARY KEY,
            lang TEXT
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS server_lang(
            guild_id INTEGER PRIMARY KEY,
            lang TEXT
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS translation_channels(
            guild_id INTEGER PRIMARY KEY,
            channels TEXT
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS error_channel(
            guild_id INTEGER PRIMARY KEY,
            channel_id INTEGER
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS bot_emote(
            guild_id INTEGER PRIMARY KEY,
            emote TEXT
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS ai_settings(
            guild_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 1
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS ai_usage(
            id INTEGER PRIMARY KEY,
            month TEXT,
            tokens INTEGER DEFAULT 0,
            cost REAL DEFAULT 0
        )
        """)
        await db.commit()

# -----------------------
# AI settings
# -----------------------
async def set_ai_enabled(guild_id: int, enabled: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO ai_settings(guild_id, enabled)
        VALUES (?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET enabled=excluded.enabled
        """, (guild_id, int(enabled)))
        await db.commit()

async def get_ai_enabled(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT enabled FROM ai_settings WHERE guild_id=?", (guild_id,)) as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row else True

# -----------------------
# AI usage tracking
# -----------------------
def _current_month():
    return time.strftime("%Y-%m")

async def add_ai_usage(tokens: int, cost: float):
    month = _current_month()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO ai_usage(month, tokens, cost)
        VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            tokens = tokens + excluded.tokens,
            cost = cost + excluded.cost
        """, (month, tokens, cost))
        await db.commit()

async def get_current_ai_usage():
    month = _current_month()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
        SELECT tokens, cost FROM ai_usage
        WHERE month=? ORDER BY id DESC LIMIT 1
        """, (month,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return 0, 0.0
            return row[0], row[1]