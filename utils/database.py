# utils/database.py
# Central async DB helpers for Zephyra
# Uses SQLite via aiosqlite. Creates all required tables if missing.

import os
import aiosqlite
from typing import List, Optional, Tuple

# Storage path (works on Koyeb). You can override with env BOT_DB_PATH
DB_PATH = os.getenv("BOT_DB_PATH", "/mnt/data/zephyra.db")

# -----------------------------
# Core connection helper
# -----------------------------
async def get_conn() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute("PRAGMA foreign_keys=ON;")
    return db

# -----------------------------
# Base tables (language, channels, emote, etc.)
# -----------------------------
async def _ensure_base_tables(db: aiosqlite.Connection):
    await db.execute("""
        CREATE TABLE IF NOT EXISTS user_lang(
            user_id    INTEGER PRIMARY KEY,
            lang       TEXT
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS server_lang(
            guild_id   INTEGER PRIMARY KEY,
            lang       TEXT
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS translation_channels(
            guild_id   INTEGER PRIMARY KEY,
            channels   TEXT
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS error_channel(
            guild_id   INTEGER PRIMARY KEY,
            channel_id INTEGER
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS bot_emote(
            guild_id   INTEGER PRIMARY KEY,
            emote      TEXT
        )
    """)
    # Optional: track monthly AI usage (tokens/cost). Harmless if unused.
    await db.execute("""
        CREATE TABLE IF NOT EXISTS ai_usage(
            month   TEXT PRIMARY KEY,   -- e.g. '2025-11'
            tokens  INTEGER DEFAULT 0,
            eur     REAL    DEFAULT 0.0
        )
    """)

# -----------------------------
# XP table
# -----------------------------
async def _ensure_xp_table(db: aiosqlite.Connection):
    await db.execute("""
        CREATE TABLE IF NOT EXISTS xp(
            guild_id       INTEGER NOT NULL,
            user_id        INTEGER NOT NULL,
            xp             INTEGER DEFAULT 0,
            messages       INTEGER DEFAULT 0,
            translations   INTEGER DEFAULT 0,
            voice_seconds  INTEGER DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        )
    """)

# -----------------------------
# Public bootstrap (call this on boot)
# -----------------------------
async def ensure_tables():
    db = await get_conn()
    try:
        await _ensure_base_tables(db)
        await _ensure_xp_table(db)
        await db.commit()
    finally:
        await db.close()

# =========================================================
# Language per user / server defaults
# =========================================================
async def set_user_lang(user_id: int, lang: str):
    db = await get_conn()
    try:
        await db.execute("""
            INSERT INTO user_lang(user_id, lang)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET lang=excluded.lang
        """, (user_id, lang))
        await db.commit()
    finally:
        await db.close()

async def get_user_lang(user_id: int) -> Optional[str]:
    db = await get_conn()
    try:
        cur = await db.execute("SELECT lang FROM user_lang WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row else None
    finally:
        await db.close()

async def set_server_lang(guild_id: int, lang: str):
    db = await get_conn()
    try:
        await db.execute("""
            INSERT INTO server_lang(guild_id, lang)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET lang=excluded.lang
        """, (guild_id, lang))
        await db.commit()
    finally:
        await db.close()

async def get_server_lang(guild_id: int) -> Optional[str]:
    db = await get_conn()
    try:
        cur = await db.execute("SELECT lang FROM server_lang WHERE guild_id=?", (guild_id,))
        row = await cur.fetchone()
        return row[0] if row else None
    finally:
        await db.close()

# =========================================================
# Channels & error channel & emote
# =========================================================
async def set_translation_channels(guild_id: int, channels: List[int]):
    db = await get_conn()
    try:
        channels_str = ",".join(map(str, channels))
        await db.execute("""
            INSERT INTO translation_channels(guild_id, channels)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET channels=excluded.channels
        """, (guild_id, channels_str))
        await db.commit()
    finally:
        await db.close()

async def get_translation_channels(guild_id: int) -> List[int]:
    db = await get_conn()
    try:
        cur = await db.execute("SELECT channels FROM translation_channels WHERE guild_id=?", (guild_id,))
        row = await cur.fetchone()
        if not row or not row[0]:
            return []
        return [int(x) for x in row[0].split(",") if x]
    finally:
        await db.close()

async def set_error_channel(guild_id: int, channel_id: Optional[int]):
    db = await get_conn()
    try:
        await db.execute("""
            INSERT INTO error_channel(guild_id, channel_id)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET channel_id=excluded.channel_id
        """, (guild_id, channel_id))
        await db.commit()
    finally:
        await db.close()

async def get_error_channel(guild_id: int) -> Optional[int]:
    db = await get_conn()
    try:
        cur = await db.execute("SELECT channel_id FROM error_channel WHERE guild_id=?", (guild_id,))
        row = await cur.fetchone()
        return int(row[0]) if row and row[0] is not None else None
    finally:
        await db.close()

async def set_bot_emote(guild_id: int, emote: str):
    db = await get_conn()
    try:
        await db.execute("""
            INSERT INTO bot_emote(guild_id, emote)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET emote=excluded.emote
        """, (guild_id, emote))
        await db.commit()
    finally:
        await db.close()

async def get_bot_emote(guild_id: int) -> Optional[str]:
    db = await get_conn()
    try:
        cur = await db.execute("SELECT emote FROM bot_emote WHERE guild_id=?", (guild_id,))
        row = await cur.fetchone()
        return row[0] if row else None
    finally:
        await db.close()

# =========================================================
# XP read/write helpers
# =========================================================
async def add_xp(
    guild_id: int,
    user_id: int,
    delta_xp: int = 0,
    delta_messages: int = 0,
    delta_translations: int = 0,
    delta_voice_seconds: int = 0
):
    """
    Upserts a row for (guild_id, user_id) and adds the deltas.
    """
    db = await get_conn()
    try:
        # Ensure row exists
        await db.execute("""
            INSERT INTO xp (guild_id, user_id, xp, messages, translations, voice_seconds)
            VALUES (?, ?, 0, 0, 0, 0)
            ON CONFLICT(guild_id, user_id) DO NOTHING
        """, (guild_id, user_id))

        # Apply increments
        await db.execute("""
            UPDATE xp
            SET xp = xp + ?,
                messages = messages + ?,
                translations = translations + ?,
                voice_seconds = voice_seconds + ?
            WHERE guild_id=? AND user_id=?
        """, (delta_xp, delta_messages, delta_translations, delta_voice_seconds, guild_id, user_id))
        await db.commit()
    finally:
        await db.close()

async def get_xp(guild_id: int, user_id: int) -> Tuple[int, int, int, int]:
    """
    Returns (xp, messages, translations, voice_seconds). Returns zeros if absent.
    """
    db = await get_conn()
    try:
        cur = await db.execute("""
            SELECT xp, messages, translations, voice_seconds
            FROM xp WHERE guild_id=? AND user_id=?
        """, (guild_id, user_id))
        row = await cur.fetchone()
        if not row:
            return (0, 0, 0, 0)
        return (int(row[0]), int(row[1]), int(row[2]), int(row[3]))
    finally:
        await db.close()

async def get_xp_leaderboard(guild_id: int, limit: int = 10, offset: int = 0):
    """
    Returns rows of (user_id, xp, messages, translations, voice_seconds),
    ordered by xp desc.
    """
    db = await get_conn()
    try:
        cur = await db.execute("""
            SELECT user_id, xp, messages, translations, voice_seconds
            FROM xp
            WHERE guild_id=?
            ORDER BY xp DESC
            LIMIT ? OFFSET ?
        """, (guild_id, limit, offset))
        rows = await cur.fetchall()
        return [(int(r[0]), int(r[1]), int(r[2]), int(r[3]), int(r[4])) for r in rows]
    finally:
        await db.close()
