# utils/database.py
# Persistent SQLite storage for Zephyra (messages, translations, voice, prefs, guild config, bot prefs)
import os
from typing import Optional, List, Tuple
import aiosqlite

DB_PATH = os.getenv("BOT_DB_PATH", "/mnt/data/bot_data.db")

# ---------- low-level helpers ----------
async def _connect() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute("PRAGMA synchronous=NORMAL;")
    await db.execute("PRAGMA foreign_keys=ON;")
    return db

async def _exec(db: aiosqlite.Connection, sql: str, params: Tuple = ()) -> None:
    cur = await db.execute(sql, params)
    await cur.close()

async def _one(db: aiosqlite.Connection, sql: str, params: Tuple = ()):
    cur = await db.execute(sql, params)
    row = await cur.fetchone()
    await cur.close()
    return row

async def _all(db: aiosqlite.Connection, sql: str, params: Tuple = ()):
    cur = await db.execute(sql, params)
    rows = await cur.fetchall()
    await cur.close()
    return rows

# ---------- schema ----------
async def ensure_schema() -> None:
    db = await _connect()
    try:
        # XP table
        await _exec(
            db,
            """
            CREATE TABLE IF NOT EXISTS xp (
                guild_id      INTEGER NOT NULL,
                user_id       INTEGER NOT NULL,
                xp            INTEGER NOT NULL DEFAULT 0,
                messages      INTEGER NOT NULL DEFAULT 0,
                translations  INTEGER NOT NULL DEFAULT 0,
                voice_seconds INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            );
            """
        )

        # Guild settings (default language, translation mode)
        await _exec(
            db,
            """
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id         INTEGER PRIMARY KEY,
                target_lang      TEXT,
                translation_mode TEXT DEFAULT 'all',
                created_at       TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # Channel allow-list for translations
        await _exec(
            db,
            """
            CREATE TABLE IF NOT EXISTS translate_channels (
                guild_id  INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                PRIMARY KEY (guild_id, channel_id)
            );
            """
        )

        # User language preferences
        await _exec(
            db,
            """
            CREATE TABLE IF NOT EXISTS user_prefs (
                user_id   INTEGER PRIMARY KEY,
                lang_code TEXT
            );
            """
        )

        # Bot per-guild preferences (e.g., reaction emote)
        await _exec(
            db,
            """
            CREATE TABLE IF NOT EXISTS bot_prefs (
                guild_id  INTEGER PRIMARY KEY,
                bot_emote TEXT
            );
            """
        )

        await db.commit()
    finally:
        await db.close()

# ---------- XP mutators ----------
async def _upsert_base(db: aiosqlite.Connection, gid: int, uid: int) -> None:
    await _exec(
        db,
        """
        INSERT INTO xp (guild_id, user_id) VALUES (?, ?)
        ON CONFLICT(guild_id, user_id) DO NOTHING;
        """,
        (gid, uid),
    )

async def add_message_xp(guild_id: int, user_id: int, delta_xp: int) -> None:
    db = await _connect()
    try:
        await _upsert_base(db, guild_id, user_id)
        await _exec(
            db,
            """
            UPDATE xp
               SET xp = xp + ?, messages = messages + 1
             WHERE guild_id = ? AND user_id = ?;
            """,
            (max(0, int(delta_xp)), guild_id, user_id),
        )
        await db.commit()
    finally:
        await db.close()

async def add_translation_xp(guild_id: int, user_id: int, delta_xp: int) -> None:
    db = await _connect()
    try:
        await _upsert_base(db, guild_id, user_id)
        await _exec(
            db,
            """
            UPDATE xp
               SET xp = xp + ?, translations = translations + 1
             WHERE guild_id = ? AND user_id = ?;
            """,
            (max(0, int(delta_xp)), guild_id, user_id),
        )
        await db.commit()
    finally:
        await db.close()

async def add_voice_seconds(guild_id: int, user_id: int, seconds: int) -> None:
    if seconds <= 0:
        return
    db = await _connect()
    try:
        await _upsert_base(db, guild_id, user_id)
        await _exec(
            db,
            """
            UPDATE xp
               SET voice_seconds = voice_seconds + ?
             WHERE guild_id = ? AND user_id = ?;
            """,
            (int(seconds), guild_id, user_id),
        )
        await db.commit()
    finally:
        await db.close()

async def add_activity(guild_id: int, user_id: int, xp: int = 0, translations: int = 0, messages: int = 0, voice_seconds: int = 0) -> None:
    """One call to update multiple counters atomically."""
    if xp < 0: xp = 0
    db = await _connect()
    try:
        await _upsert_base(db, guild_id, user_id)
        await _exec(
            db,
            """
            UPDATE xp
               SET xp = xp + ?,
                   translations = translations + ?,
                   messages = messages + ?,
                   voice_seconds = voice_seconds + ?
             WHERE guild_id = ? AND user_id = ?;
            """,
            (int(xp), int(translations), int(messages), int(voice_seconds), guild_id, user_id),
        )
        await db.commit()
    finally:
        await db.close()

# ---------- XP queries ----------
async def get_xp(guild_id: int, user_id: int) -> Tuple[int, int, int, int]:
    db = await _connect()
    try:
        row = await _one(
            db,
            """SELECT xp, messages, translations, voice_seconds
                 FROM xp
                WHERE guild_id = ? AND user_id = ?;""",
            (guild_id, user_id),
        )
        if not row:
            return (0, 0, 0, 0)
        return (int(row[0]), int(row[1]), int(row[2]), int(row[3]))
    finally:
        await db.close()

LEADERBOARD_PAGE = 10

async def get_xp_leaderboard(guild_id: int, limit: int = LEADERBOARD_PAGE, offset: int = 0):
    db = await _connect()
    try:
        rows = await _all(
            db,
            """
            SELECT user_id, xp, messages, translations, voice_seconds
              FROM xp
             WHERE guild_id = ?
             ORDER BY xp DESC, messages DESC
             LIMIT ? OFFSET ?;
            """,
            (guild_id, int(limit), int(offset)),
        )
        return rows
    finally:
        await db.close()

# ---------- Translation channel allow-list ----------
async def get_translation_channels(guild_id: int) -> Optional[List[int]]:
    db = await _connect()
    try:
        rows = await _all(
            db,
            "SELECT channel_id FROM translate_channels WHERE guild_id = ?;",
            (guild_id,),
        )
        if not rows:
            return None  # None → allow in all channels
        return [int(r[0]) for r in rows]
    finally:
        await db.close()

async def allow_translation_channel(guild_id: int, channel_id: int) -> None:
    db = await _connect()
    try:
        await _exec(
            db,
            "INSERT OR IGNORE INTO translate_channels (guild_id, channel_id) VALUES (?, ?);",
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
            "DELETE FROM translate_channels WHERE guild_id = ? AND channel_id = ?;",
            (guild_id, channel_id),
        )
        await db.commit()
    finally:
        await db.close()

# ---------- User prefs ----------
async def set_user_lang(user_id: int, code: str) -> None:
    db = await _connect()
    try:
        await _exec(
            db,
            """
            INSERT INTO user_prefs (user_id, lang_code) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET lang_code = excluded.lang_code;
            """,
            (user_id, code),
        )
        await db.commit()
    finally:
        await db.close()

async def get_user_lang(user_id: int) -> Optional[str]:
    db = await _connect()
    try:
        row = await _one(db, "SELECT lang_code FROM user_prefs WHERE user_id = ?;", (user_id,))
        return row[0] if row else None
    finally:
        await db.close()

# ---------- Server default language ----------
async def set_server_lang(guild_id: int, code: str) -> None:
    db = await _connect()
    try:
        await _exec(
            db,
            """
            INSERT INTO guild_settings (guild_id, target_lang)
                 VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET target_lang = excluded.target_lang;
            """,
            (guild_id, code),
        )
        await db.commit()
    finally:
        await db.close()

async def get_server_lang(guild_id: int) -> Optional[str]:
    db = await _connect()
    try:
        row = await _one(db, "SELECT target_lang FROM guild_settings WHERE guild_id = ?;", (guild_id,))
        return row[0] if row else None
    finally:
        await db.close()

# ---------- Bot prefs (emote) ----------
async def set_bot_emote(guild_id: int, emote: str) -> None:
    db = await _connect()
    try:
        await _exec(
            db,
            """
            INSERT INTO bot_prefs (guild_id, bot_emote)
                 VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET bot_emote = excluded.bot_emote;
            """,
            (guild_id, emote),
        )
        await db.commit()
    finally:
        await db.close()

async def get_bot_emote(guild_id: int) -> Optional[str]:
    db = await _connect()
    try:
        row = await _one(db, "SELECT bot_emote FROM bot_prefs WHERE guild_id = ?;", (guild_id,))
        return row[0] if row else None
    finally:
        await db.close()
