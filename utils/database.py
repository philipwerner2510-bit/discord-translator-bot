# utils/database.py
import os
import json
import aiosqlite
import pathlib
from typing import Optional, List, Tuple

DB_PATH = os.getenv("BOT_DB_PATH", "/mnt/data/bot_data.db")

# -----------------------
# Schema init
# -----------------------
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA synchronous=NORMAL;")
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
        # Analytics tables
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_translations(
                user_id INTEGER PRIMARY KEY,
                count INTEGER NOT NULL DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_translations(
                guild_id INTEGER PRIMARY KEY,
                count INTEGER NOT NULL DEFAULT 0
            )
        """)
        await db.commit()

# -----------------------
# Export DB (backup)
# -----------------------
async def export_db(output_path: str) -> str:
    """
    Exports the live database to output_path using SQLite VACUUM INTO.
    Returns the absolute path of the backup file.
    """
    p = pathlib.Path(output_path).expanduser().resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    safe = str(p).replace("'", "''")
    async with aiosqlite.connect(DB_PATH) as db:
        # Note: parameter binding isn’t supported for INTO path; escape single quotes.
        await db.execute(f"VACUUM INTO '{safe}';")
        await db.commit()
    return str(p)

# -----------------------
# User language
# -----------------------
async def set_user_lang(user_id: int, lang: str) -> None:
    lang = (lang or "").strip().lower()[:16]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO user_lang(user_id, lang)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET lang=excluded.lang
        """, (user_id, lang))
        await db.commit()

async def get_user_lang(user_id: int) -> Optional[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT lang FROM user_lang WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

# -----------------------
# Server default language
# -----------------------
async def set_server_lang(guild_id: int, lang: str) -> None:
    lang = (lang or "").strip().lower()[:16]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO server_lang(guild_id, lang)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET lang=excluded.lang
        """, (guild_id, lang))
        await db.commit()

async def get_server_lang(guild_id: int) -> Optional[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT lang FROM server_lang WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

# -----------------------
# Translation channels
# -----------------------
async def set_translation_channels(guild_id: int, channels: List[int]) -> None:
    # store as JSON for future flexibility; keep CSV back-compat in getter
    payload = json.dumps([int(c) for c in channels])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO translation_channels(guild_id, channels)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET channels=excluded.channels
        """, (guild_id, payload))
        await db.commit()

async def get_translation_channels(guild_id: int) -> List[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT channels FROM translation_channels WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
            if not row or row[0] is None:
                return []
            raw = row[0]
            # JSON first
            try:
                return [int(x) for x in json.loads(raw)]
            except Exception:
                # CSV fallback for older rows
                return [int(x) for x in raw.split(",") if x.strip().isdigit()]

# -----------------------
# Error channel
# -----------------------
async def set_error_channel(guild_id: int, channel_id: Optional[int]) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO error_channel(guild_id, channel_id)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET channel_id=excluded.channel_id
        """, (guild_id, channel_id))
        await db.commit()

async def get_error_channel(guild_id: int) -> Optional[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT channel_id FROM error_channel WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
            return int(row[0]) if row and row[0] is not None else None

# -----------------------
# Bot emote
# -----------------------
async def set_bot_emote(guild_id: int, emote: str) -> None:
    emote = (emote or "").strip()[:128]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO bot_emote(guild_id, emote)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET emote=excluded.emote
        """, (guild_id, emote))
        await db.commit()

async def get_bot_emote(guild_id: int) -> Optional[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT emote FROM bot_emote WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

# -----------------------
# Analytics counters
# -----------------------
async def increment_user_counter(user_id: int, amt: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO user_translations(user_id, count)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET count = count + excluded.count
        """, (user_id, amt))
        await db.commit()

async def increment_guild_counter(guild_id: int, amt: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO guild_translations(guild_id, count)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET count = count + excluded.count
        """, (guild_id, amt))
        await db.commit()

async def get_user_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT count FROM user_translations WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            return int(row[0]) if row else 0

async def get_guild_count(guild_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT count FROM guild_translations WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
            return int(row[0]) if row else 0

async def get_top_users(limit: int = 10) -> List[Tuple[int, int]]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT user_id, count FROM user_translations
            ORDER BY count DESC
            LIMIT ?
        """, (limit,)) as cur:
            rows = await cur.fetchall()
            return [(int(uid), int(cnt)) for (uid, cnt) in rows]