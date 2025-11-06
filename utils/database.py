# utils/database.py
# Full persistent database module for Zephyra ✅
# Includes: XP system, language settings, AI settings, translation logging

import aiosqlite
import os
from datetime import datetime

DB_PATH = os.getenv("BOT_DB_PATH", "/mnt/data/bot_data.db")

# -----------------------
# DB Initialization
# -----------------------

async def ensure_tables():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA synchronous=NORMAL;")

        # Language per user
        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_lang (
            user_id INTEGER PRIMARY KEY,
            lang    TEXT NOT NULL
        );
        """)

        # Language per guild
        await db.execute("""
        CREATE TABLE IF NOT EXISTS server_lang (
            guild_id INTEGER PRIMARY KEY,
            lang     TEXT NOT NULL
        );
        """)

        # Translation-enabled channels (CSV list)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS translation_channels (
            guild_id   INTEGER PRIMARY KEY,
            channels   TEXT NOT NULL
        );
        """)

        # Error log channels
        await db.execute("""
        CREATE TABLE IF NOT EXISTS error_channel (
            guild_id   INTEGER PRIMARY KEY,
            channel_id INTEGER NOT NULL
        );
        """)

        # Custom emote per guild
        await db.execute("""
        CREATE TABLE IF NOT EXISTS bot_emote (
            guild_id INTEGER PRIMARY KEY,
            emote    TEXT NOT NULL
        );
        """)

        # XP + tracking
        await db.execute("""
        CREATE TABLE IF NOT EXISTS xp (
            guild_id       INTEGER NOT NULL,
            user_id        INTEGER NOT NULL,
            xp             INTEGER NOT NULL DEFAULT 0,
            messages       INTEGER NOT NULL DEFAULT 0,
            translations   INTEGER NOT NULL DEFAULT 0,
            voice_seconds  INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        );
        """)

        # Helpful indexes
        await db.execute("CREATE INDEX IF NOT EXISTS idx_xp_guild ON xp(guild_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_xp_user ON xp(user_id);")

        # AI usage tracking
        await db.execute("""
        CREATE TABLE IF NOT EXISTS ai_usage (
            month   TEXT PRIMARY KEY,   -- 'YYYY-MM'
            tokens  INTEGER NOT NULL DEFAULT 0,
            eur     REAL    NOT NULL DEFAULT 0.0
        );
        """)

        # AI feature settings per guild
        await db.execute("""
        CREATE TABLE IF NOT EXISTS ai_settings (
            guild_id   INTEGER PRIMARY KEY,
            ai_enabled INTEGER NOT NULL DEFAULT 1,
            model      TEXT NOT NULL DEFAULT 'gpt-4o-mini'
        );
        """)

        await db.commit()


# -----------------------
# Language Get / Set
# -----------------------

async def get_user_lang(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        row = await db.execute_fetchone("SELECT lang FROM user_lang WHERE user_id=?", (user_id,))
        return row[0] if row else None

async def set_user_lang(user_id, lang):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "REPLACE INTO user_lang (user_id, lang) VALUES (?, ?)",
            (user_id, lang)
        )
        await db.commit()


async def get_server_lang(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        row = await db.execute_fetchone("SELECT lang FROM server_lang WHERE guild_id=?", (guild_id,))
        return row[0] if row else None

async def set_server_lang(guild_id, lang):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "REPLACE INTO server_lang (guild_id, lang) VALUES (?, ?)",
            (guild_id, lang)
        )
        await db.commit()


# -----------------------
# Translation Channels
# -----------------------

async def get_translation_channels(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        row = await db.execute_fetchone(
            "SELECT channels FROM translation_channels WHERE guild_id=?", (guild_id,)
        )
        if not row: return []
        return [int(x) for x in row[0].split(",") if x]

async def set_translation_channels(guild_id, channel_ids):
    channels = ",".join(str(c) for c in channel_ids)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "REPLACE INTO translation_channels (guild_id, channels) VALUES (?, ?)",
            (guild_id, channels)
        )
        await db.commit()


# -----------------------
# Error Channel
# -----------------------

async def get_error_channel(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        row = await db.execute_fetchone(
            "SELECT channel_id FROM error_channel WHERE guild_id=?", 
            (guild_id,)
        )
        return row[0] if row else None

async def set_error_channel(guild_id, channel_id):
    async with aiosqlite.connect(DB_PATH) as db:
        if channel_id is None:
            await db.execute("DELETE FROM error_channel WHERE guild_id=?", (guild_id,))
        else:
            await db.execute(
                "REPLACE INTO error_channel (guild_id, channel_id) VALUES (?, ?)",
                (guild_id, channel_id)
            )
        await db.commit()


# -----------------------
# Custom Emote
# -----------------------

async def get_emote(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        row = await db.execute_fetchone(
            "SELECT emote FROM bot_emote WHERE guild_id=?", 
            (guild_id,)
        )
        return row[0] if row else None

async def set_emote(guild_id, emote):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "REPLACE INTO bot_emote (guild_id, emote) VALUES (?, ?)",
            (guild_id, emote)
        )
        await db.commit()


# -----------------------
# XP System
# -----------------------

async def add_xp(guild_id, user_id, amount=1, msg_inc=0, trans_inc=0, voice_inc=0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO xp (guild_id, user_id, xp, messages, translations, voice_seconds)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(guild_id, user_id) DO UPDATE SET
            xp = xp + excluded.xp,
            messages = messages + excluded.messages,
            translations = translations + excluded.translations,
            voice_seconds = voice_seconds + excluded.voice_seconds
        """, (guild_id, user_id, amount, msg_inc, trans_inc, voice_inc))
        await db.commit()

async def get_xp(guild_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        row = await db.execute_fetchone("""
        SELECT xp, messages, translations, voice_seconds 
        FROM xp WHERE guild_id=? AND user_id=?""", 
        (guild_id, user_id))
        return row if row else (0, 0, 0, 0)

async def get_xp_leaderboard(guild_id, limit, offset):
    async with aiosqlite.connect(DB_PATH) as db:
        rows = await db.execute_fetchall(f"""
        SELECT user_id, xp, messages, translations, voice_seconds
        FROM xp
        WHERE guild_id=?
        ORDER BY xp DESC
        LIMIT {limit} OFFSET {offset}
        """, (guild_id,))
        return rows


# -----------------------
# AI Usage
# -----------------------

def _current_month():
    return datetime.utcnow().strftime("%Y-%m")

async def add_ai_usage(tokens, eur):
    async with aiosqlite.connect(DB_PATH) as db:
        month = _current_month()
        await db.execute("""
        INSERT INTO ai_usage (month, tokens, eur)
        VALUES (?, ?, ?)
        ON CONFLICT(month) DO UPDATE SET
            tokens = tokens + excluded.tokens,
            eur = eur + excluded.eur;
        """, (month, tokens, eur))
        await db.commit()

async def get_ai_usage():
    async with aiosqlite.connect(DB_PATH) as db:
        rows = await db.execute_fetchall("""
        SELECT month, tokens, eur FROM ai_usage ORDER BY month DESC LIMIT 12;
        """)
        return rows


# -----------------------
# AI Settings
# -----------------------

async def set_ai_settings(guild_id, enabled=None, model=None):
    async with aiosqlite.connect(DB_PATH) as db:
        current = await db.execute_fetchone("SELECT ai_enabled, model FROM ai_settings WHERE guild_id=?", (guild_id,))
        ai_enabled, current_model = current if current else (1, "gpt-4o-mini")

        if enabled is not None:
            ai_enabled = 1 if enabled else 0
        if model:
            current_model = model

        await db.execute("""
        REPLACE INTO ai_settings (guild_id, ai_enabled, model)
        VALUES (?, ?, ?)
        """, (guild_id, ai_enabled, current_model))
        await db.commit()

async def get_ai_settings(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        row = await db.execute_fetchone(
            "SELECT ai_enabled, model FROM ai_settings WHERE guild_id=?", 
            (guild_id,)
        )
        return row if row else (1, "gpt-4o-mini")
