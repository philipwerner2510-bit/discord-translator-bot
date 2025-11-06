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
    await db.execute("""
        CREATE TABLE IF NOT EXISTS ai_usage(
            month   TEXT PRIMARY KEY,   -- e.g. '2025-11'
            tokens  INTEGER DEFAULT 0,
            eur     REAL    DEFAULT 0.0
        )
    """)

# -----------------------------
# XP & Config tables
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

async def _ensure_xp_config_table(db: aiosqlite.Connection):
    # Defaults mirror common bot curves; admin can change via /xpconfig
    await db.execute("""
        CREATE TABLE IF NOT EXISTS xp_config(
            guild_id            INTEGER PRIMARY KEY,
            msg_xp_min          INTEGER DEFAULT 10,
            msg_xp_max          INTEGER DEFAULT 15,
            translate_xp        INTEGER DEFAULT 20,
            voice_xp_per_min    INTEGER DEFAULT 3,
            announce_levelups   INTEGER DEFAULT 1,
            prestige_threshold  INTEGER DEFAULT 100_000
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
        await _ensure_xp_config_table(db)
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
    db = await get_conn()
    try:
        await db.execute("""
            INSERT INTO xp (guild_id, user_id, xp, messages, translations, voice_seconds)
            VALUES (?, ?, 0, 0, 0, 0)
            ON CONFLICT(guild_id, user_id) DO NOTHING
        """, (guild_id, user_id))

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

# =========================================================
# XP Config helpers
# =========================================================
async def get_xp_config(guild_id: int):
    db = await get_conn()
    try:
        cur = await db.execute("""
            SELECT msg_xp_min, msg_xp_max, translate_xp, voice_xp_per_min, announce_levelups, prestige_threshold
            FROM xp_config WHERE guild_id=?
        """, (guild_id,))
        row = await cur.fetchone()
        if row:
            return {
                "msg_xp_min": row[0],
                "msg_xp_max": row[1],
                "translate_xp": row[2],
                "voice_xp_per_min": row[3],
                "announce_levelups": bool(row[4]),
                "prestige_threshold": row[5],
            }
        # Defaults if not set
        return {
            "msg_xp_min": 10,
            "msg_xp_max": 15,
            "translate_xp": 20,
            "voice_xp_per_min": 3,
            "announce_levelups": True,
            "prestige_threshold": 100_000,
        }
    finally:
        await db.close()

async def set_xp_config(
    guild_id: int,
    msg_xp_min: Optional[int] = None,
    msg_xp_max: Optional[int] = None,
    translate_xp: Optional[int] = None,
    voice_xp_per_min: Optional[int] = None,
    announce_levelups: Optional[bool] = None,
    prestige_threshold: Optional[int] = None,
):
    db = await get_conn()
    try:
        # upsert row first
        await db.execute("""
            INSERT INTO xp_config(guild_id)
            VALUES (?)
            ON CONFLICT(guild_id) DO NOTHING
        """, (guild_id,))
        # build dynamic update
        fields = []
        params = []
        if msg_xp_min is not None:
            fields.append("msg_xp_min=?")
            params.append(msg_xp_min)
        if msg_xp_max is not None:
            fields.append("msg_xp_max=?")
            params.append(msg_xp_max)
        if translate_xp is not None:
            fields.append("translate_xp=?")
            params.append(translate_xp)
        if voice_xp_per_min is not None:
            fields.append("voice_xp_per_min=?")
            params.append(voice_xp_per_min)
        if announce_levelups is not None:
            fields.append("announce_levelups=?")
            params.append(1 if announce_levelups else 0)
        if prestige_threshold is not None:
            fields.append("prestige_threshold=?")
            params.append(prestige_threshold)

        if fields:
            sql = f"UPDATE xp_config SET {', '.join(fields)} WHERE guild_id=?"
            params.append(guild_id)
            await db.execute(sql, tuple(params))
            await db.commit()
    finally:
        await db.close()
