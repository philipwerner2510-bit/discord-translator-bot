# utils/database.py
# Persistent SQLite storage for Zephyra (xp, prefs, guild config, roles)
import os
from typing import Optional, List, Tuple
import aiosqlite

DB_PATH = os.getenv("BOT_DB_PATH", "/mnt/data/bot_data.db")

# ---------- low-level ----------
async def _connect() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    # sensible pragmas for a bot
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute("PRAGMA synchronous=NORMAL;")
    await db.execute("PRAGMA foreign_keys=ON;")
    return db

async def _exec(db: aiosqlite.Connection, sql: str, params: tuple = ()) -> None:
    cur = await db.execute(sql, params)
    await cur.close()

async def _one(db: aiosqlite.Connection, sql: str, params: tuple = ()):
    cur = await db.execute(sql, params)
    row = await cur.fetchone()
    await cur.close()
    return row

async def _all(db: aiosqlite.Connection, sql: str, params: tuple = ()):
    cur = await db.execute(sql, params)
    rows = await cur.fetchall()
    await cur.close()
    return rows

# ---------- schema (with migrations) ----------
async def ensure_schema() -> None:
    """
    Creates tables if missing and performs lightweight migrations
    so older DBs continue working (e.g., add server_lang column).
    """
    db = await _connect()
    try:
        # XP
        await _exec(db, """
        CREATE TABLE IF NOT EXISTS xp(
          guild_id      INTEGER NOT NULL,
          user_id       INTEGER NOT NULL,
          xp            INTEGER NOT NULL DEFAULT 0,
          messages      INTEGER NOT NULL DEFAULT 0,
          translations  INTEGER NOT NULL DEFAULT 0,
          voice_seconds INTEGER NOT NULL DEFAULT 0,
          PRIMARY KEY(guild_id, user_id)
        );
        """)

        # Guild settings (server_lang may be added later by migration)
        await _exec(db, """
        CREATE TABLE IF NOT EXISTS guild_settings(
          guild_id   INTEGER PRIMARY KEY,
          -- server_lang TEXT  -- may be missing in older DBs; migration below adds it
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Translation channel allow-list
        await _exec(db, """
        CREATE TABLE IF NOT EXISTS translate_channels(
          guild_id  INTEGER NOT NULL,
          channel_id INTEGER NOT NULL,
          PRIMARY KEY(guild_id, channel_id)
        );
        """)

        # User language preference
        await _exec(db, """
        CREATE TABLE IF NOT EXISTS user_prefs(
          user_id   INTEGER PRIMARY KEY,
          lang_code TEXT
        );
        """)

        # Guild meta: error channel + bot emote
        await _exec(db, """
        CREATE TABLE IF NOT EXISTS guild_meta(
          guild_id         INTEGER PRIMARY KEY,
          error_channel_id INTEGER,
          bot_emote        TEXT
        );
        """)

        # Level role table mapping (every 10 levels: 1-10, 11-20, ..., 91-100)
        await _exec(db, """
        CREATE TABLE IF NOT EXISTS level_roles(
          guild_id  INTEGER NOT NULL,
          lvl_start INTEGER NOT NULL,
          lvl_end   INTEGER NOT NULL,
          role_id   INTEGER NOT NULL,
          PRIMARY KEY(guild_id, lvl_start, lvl_end)
        );
        """)

        # -------- migrations --------
        # Add server_lang column if missing (fixes "no such column: server_lang")
        info = await _all(db, "PRAGMA table_info(guild_settings);")
        cols = {r[1] for r in info}  # r[1] = column name
        if "server_lang" not in cols:
            await _exec(db, "ALTER TABLE guild_settings ADD COLUMN server_lang TEXT;")

        await db.commit()
    finally:
        await db.close()

# ---------- XP ----------
async def _upsert_xp(db: aiosqlite.Connection, gid: int, uid: int) -> None:
    await _exec(db, "INSERT OR IGNORE INTO xp(guild_id, user_id) VALUES(?, ?)", (gid, uid))

async def add_message_xp(guild_id: int, user_id: int, delta: int) -> None:
    db = await _connect()
    try:
        await _upsert_xp(db, guild_id, user_id)
        await _exec(
            db,
            "UPDATE xp SET xp = xp + ?, messages = messages + 1 WHERE guild_id = ? AND user_id = ?",
            (max(0, int(delta)), guild_id, user_id),
        )
        await db.commit()
    finally:
        await db.close()

async def add_translation_xp(guild_id: int, user_id: int, delta: int) -> None:
    db = await _connect()
    try:
        await _upsert_xp(db, guild_id, user_id)
        await _exec(
            db,
            "UPDATE xp SET xp = xp + ?, translations = translations + 1 WHERE guild_id = ? AND user_id = ?",
            (max(0, int(delta)), guild_id, user_id),
        )
        await db.commit()
    finally:
        await db.close()

async def add_voice_seconds(guild_id: int, user_id: int, seconds: int) -> None:
    if seconds <= 0:
        return
    db = await _connect()
    try:
        await _upsert_xp(db, guild_id, user_id)
        await _exec(
            db,
            "UPDATE xp SET voice_seconds = voice_seconds + ? WHERE guild_id = ? AND user_id = ?",
            (int(seconds), guild_id, user_id),
        )
        await db.commit()
    finally:
        await db.close()

async def get_xp(guild_id: int, user_id: int) -> Tuple[int, int, int, int]:
    db = await _connect()
    try:
        row = await _one(
            db,
            "SELECT xp, messages, translations, voice_seconds FROM xp WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        return (0, 0, 0, 0) if not row else (int(row[0]), int(row[1]), int(row[2]), int(row[3]))
    finally:
        await db.close()

async def get_xp_leaderboard(guild_id: int, limit: int = 10, offset: int = 0):
    db = await _connect()
    try:
        return await _all(
            db,
            """
            SELECT user_id, xp, messages, translations, voice_seconds
              FROM xp
             WHERE guild_id = ?
             ORDER BY xp DESC, messages DESC
             LIMIT ? OFFSET ?
            """,
            (guild_id, int(limit), int(offset)),
        )
    finally:
        await db.close()

# ---------- guild language / channels / meta ----------
async def set_server_lang(guild_id: int, code: str) -> None:
    db = await _connect()
    try:
        await _exec(
            db,
            """
            INSERT INTO guild_settings(guild_id, server_lang) VALUES(?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET server_lang = excluded.server_lang
            """,
            (guild_id, code),
        )
        await db.commit()
    finally:
        await db.close()

async def get_server_lang(guild_id: int) -> Optional[str]:
    db = await _connect()
    try:
        row = await _one(db, "SELECT server_lang FROM guild_settings WHERE guild_id = ?", (guild_id,))
        return row[0] if row and row[0] else None
    finally:
        await db.close()

async def get_translation_channels(guild_id: int) -> Optional[List[int]]:
    """
    Returns a list of allowed channel IDs if any are configured;
    returns None to mean 'allow all channels'.
    """
    db = await _connect()
    try:
        rows = await _all(db, "SELECT channel_id FROM translate_channels WHERE guild_id = ?", (guild_id,))
        if not rows:
            return None
        return [int(r[0]) for r in rows]
    finally:
        await db.close()

async def allow_translation_channel(guild_id: int, channel_id: int) -> None:
    db = await _connect()
    try:
        await _exec(
            db,
            "INSERT OR IGNORE INTO translate_channels(guild_id, channel_id) VALUES(?, ?)",
            (guild_id, channel_id),
        )
        await db.commit()
    finally:
        await db.close()

async def remove_translation_channel(guild_id: int, channel_id: int) -> None:
    db = await _connect()
    try:
        await _exec(
            db,
            "DELETE FROM translate_channels WHERE guild_id = ? AND channel_id = ?",
            (guild_id, channel_id),
        )
        await db.commit()
    finally:
        await db.close()

async def set_user_lang(user_id: int, code: str) -> None:
    db = await _connect()
    try:
        await _exec(
            db,
            """
            INSERT INTO user_prefs(user_id, lang_code) VALUES(?, ?)
            ON CONFLICT(user_id) DO UPDATE SET lang_code = excluded.lang_code
            """,
            (user_id, code),
        )
        await db.commit()
    finally:
        await db.close()

async def get_user_lang(user_id: int) -> Optional[str]:
    db = await _connect()
    try:
        row = await _one(db, "SELECT lang_code FROM user_prefs WHERE user_id = ?", (user_id,))
        return row[0] if row else None
    finally:
        await db.close()

# meta: error channel & emote
async def set_error_channel(guild_id: int, channel_id: Optional[int]) -> None:
    db = await _connect()
    try:
        await _exec(
            db,
            """
            INSERT INTO guild_meta(guild_id, error_channel_id) VALUES(?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET error_channel_id = excluded.error_channel_id
            """,
            (guild_id, channel_id),
        )
        await db.commit()
    finally:
        await db.close()

async def get_error_channel(guild_id: int) -> Optional[int]:
    db = await _connect()
    try:
        row = await _one(db, "SELECT error_channel_id FROM guild_meta WHERE guild_id = ?", (guild_id,))
        return int(row[0]) if row and row[0] is not None else None
    finally:
        await db.close()

async def set_bot_emote(guild_id: int, emote: str) -> None:
    db = await _connect()
    try:
        await _exec(
            db,
            """
            INSERT INTO guild_meta(guild_id, bot_emote) VALUES(?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET bot_emote = excluded.bot_emote
            """,
            (guild_id, emote),
        )
        await db.commit()
    finally:
        await db.close()

async def get_bot_emote(guild_id: int) -> Optional[str]:
    db = await _connect()
    try:
        row = await _one(db, "SELECT bot_emote FROM guild_meta WHERE guild_id = ?", (guild_id,))
        return row[0] if row and row[0] else None
    finally:
        await db.close()

# ---------- level roles (setup/show/delete) ----------
async def upsert_role_table(guild_id: int, mapping: List[Tuple[int, int, int]]) -> None:
    """
    mapping: list of (lvl_start, lvl_end, role_id)
    Overwrites existing mapping for the guild.
    """
    db = await _connect()
    try:
        await _exec(db, "DELETE FROM level_roles WHERE guild_id = ?", (guild_id,))
        for ls, le, rid in mapping:
            await _exec(
                db,
                "INSERT INTO level_roles(guild_id, lvl_start, lvl_end, role_id) VALUES(?, ?, ?, ?)",
                (guild_id, int(ls), int(le), int(rid)),
            )
        await db.commit()
    finally:
        await db.close()

async def get_role_table(guild_id: int) -> List[Tuple[int, int, int]]:
    db = await _connect()
    try:
        rows = await _all(
            db,
            "SELECT lvl_start, lvl_end, role_id FROM level_roles WHERE guild_id = ? ORDER BY lvl_start",
            (guild_id,),
        )
        return [(int(a), int(b), int(c)) for (a, b, c) in rows]
    finally:
        await db.close()

async def delete_role_table(guild_id: int) -> int:
    db = await _connect()
    try:
        await _exec(db, "DELETE FROM level_roles WHERE guild_id = ?", (guild_id,))
        changes = db.total_changes
        await db.commit()
        return changes
    finally:
        await db.close()
