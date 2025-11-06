# utils/database.py
# Persistent SQLite storage for Zephyra (messages, translations, voice, prefs, guild config, emotes)
import os
from typing import Optional, List, Tuple
import aiosqlite

DB_PATH = os.getenv("BOT_DB_PATH", "/mnt/data/bot_data.db")

# ——— Connection helpers ———
async def _connect() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
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

# ——— Schema ———
async def ensure_schema() -> None:
    """Create all required tables if missing."""
    db = await _connect()
    try:
        # XP
        await _exec(db, """
        CREATE TABLE IF NOT EXISTS xp (
            guild_id      INTEGER NOT NULL,
            user_id       INTEGER NOT NULL,
            xp            INTEGER NOT NULL DEFAULT 0,
            messages      INTEGER NOT NULL DEFAULT 0,
            translations  INTEGER NOT NULL DEFAULT 0,
            voice_seconds INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        );
        """)

        # Guild settings (minimal set for translator)
        await _exec(db, """
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id        INTEGER PRIMARY KEY,
            target_lang     TEXT,
            translation_mode TEXT DEFAULT 'all',
            created_at      TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Allowed channels for translator reactions
        await _exec(db, """
        CREATE TABLE IF NOT EXISTS translate_channels (
            guild_id  INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            PRIMARY KEY (guild_id, channel_id)
        );
        """)

        # User language preference
        await _exec(db, """
        CREATE TABLE IF NOT EXISTS user_prefs (
            user_id   INTEGER PRIMARY KEY,
            lang_code TEXT
        );
        """)

        # Guild-level bot emote setting (for reaction-translate)
        await _exec(db, """
        CREATE TABLE IF NOT EXISTS bot_emote (
            guild_id INTEGER PRIMARY KEY,
            emote    TEXT
        );
        """)

        await db.commit()
    finally:
        await db.close()

# Backward compat name used by older boot scripts
ensure_tables = ensure_schema

# ——— XP helpers & Level math ———
# Level curve: cumulative XP to reach level N
#   cost for next level = 100 + 25*(lvl-1)
#   total_xp(lvl) = sum_{k=1..lvl-1} (100 + 25*(k-1))
def total_xp_for_level(level: int) -> int:
    if level <= 1:
        return 0
    # arithmetic series
    n = level - 1
    return int(n * 100 + 25 * (n * (n - 1) // 2))

def level_from_xp(xp: int) -> Tuple[int, int, int]:
    """Return (level, xp_into_level, xp_for_next_level)."""
    lvl = 1
    while True:
        next_total = total_xp_for_level(lvl + 1)
        if xp < next_total:
            break
        lvl += 1
        # safety
        if lvl > 1000:
            break
    curr_total = total_xp_for_level(lvl)
    into = xp - curr_total
    need = total_xp_for_level(lvl + 1) - curr_total
    return (lvl, into, need)

async def _upsert_base(db: aiosqlite.Connection, gid: int, uid: int) -> None:
    await _exec(db, """
        INSERT INTO xp (guild_id, user_id) VALUES (?, ?)
        ON CONFLICT(guild_id, user_id) DO NOTHING;
    """, (gid, uid))

async def add_activity(guild_id: int, user_id: int, *, xp: int = 0,
                       messages: int = 0, translations: int = 0, voice_seconds: int = 0) -> None:
    db = await _connect()
    try:
        await _upsert_base(db, guild_id, user_id)
        await _exec(db, """
            UPDATE xp
               SET xp = xp + ?,
                   messages = messages + ?,
                   translations = translations + ?,
                   voice_seconds = voice_seconds + ?
             WHERE guild_id = ? AND user_id = ?;
        """, (max(0, int(xp)), int(messages), int(translations), int(voice_seconds), guild_id, user_id))
        await db.commit()
    finally:
        await db.close()

# Convenience splitters
async def add_message_xp(guild_id: int, user_id: int, delta_xp: int) -> None:
    await add_activity(guild_id, user_id, xp=max(0, int(delta_xp)), messages=1)

async def add_translation_xp(guild_id: int, user_id: int, delta_xp: int) -> None:
    await add_activity(guild_id, user_id, xp=max(0, int(delta_xp)), translations=1)

async def add_voice_seconds(guild_id: int, user_id: int, seconds: int) -> None:
    if seconds > 0:
        await add_activity(guild_id, user_id, voice_seconds=int(seconds))

async def get_xp(guild_id: int, user_id: int) -> Tuple[int, int, int, int]:
    db = await _connect()
    try:
        row = await _one(db, """
            SELECT xp, messages, translations, voice_seconds
              FROM xp
             WHERE guild_id = ? AND user_id = ?;
        """, (guild_id, user_id))
        if not row:
            return (0, 0, 0, 0)
        return (int(row[0]), int(row[1]), int(row[2]), int(row[3]))
    finally:
        await db.close()

LEADERBOARD_PAGE = 10

async def get_xp_leaderboard(guild_id: int, limit: int = LEADERBOARD_PAGE, offset: int = 0):
    db = await _connect()
    try:
        rows = await _all(db, """
            SELECT user_id, xp, messages, translations, voice_seconds
              FROM xp
             WHERE guild_id = ?
             ORDER BY xp DESC, messages DESC
             LIMIT ? OFFSET ?;
        """, (guild_id, int(limit), int(offset)))
        return rows
    finally:
        await db.close()

# ——— Translator config ———
async def get_translation_channels(guild_id: int) -> Optional[List[int]]:
    db = await _connect()
    try:
        rows = await _all(db, "SELECT channel_id FROM translate_channels WHERE guild_id = ?;", (guild_id,))
        if not rows:
            return None
        return [int(r[0]) for r in rows]
    finally:
        await db.close()

async def allow_translation_channel(guild_id: int, channel_id: int) -> None:
    db = await _connect()
    try:
        await _exec(db, "INSERT OR IGNORE INTO translate_channels (guild_id, channel_id) VALUES (?, ?);",
                    (guild_id, channel_id))
        await db.commit()
    finally:
        await db.close()

async def remove_translation_channel(guild_id: int, channel_id: int) -> None:
    db = await _connect()
    try:
        await _exec(db, "DELETE FROM translate_channels WHERE guild_id = ? AND channel_id = ?;",
                    (guild_id, channel_id))
        await db.commit()
    finally:
        await db.close()

# ——— User language prefs ———
async def set_user_lang(user_id: int, code: str) -> None:
    db = await _connect()
    try:
        await _exec(db, """
            INSERT INTO user_prefs (user_id, lang_code) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET lang_code = excluded.lang_code;
        """, (user_id, code))
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

# ——— Bot emote config ———
async def set_bot_emote(guild_id: int, emote: str) -> None:
    db = await _connect()
    try:
        await _exec(db, """
            INSERT INTO bot_emote (guild_id, emote) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET emote = excluded.emote;
        """, (guild_id, emote.strip()))
        await db.commit()
    finally:
        await db.close()

async def get_bot_emote(guild_id: int) -> Optional[str]:
    db = await _connect()
    try:
        row = await _one(db, "SELECT emote FROM bot_emote WHERE guild_id = ?;", (guild_id,))
        return row[0] if row else None
    finally:
        await db.close()
