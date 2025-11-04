# utils/database.py  (UPDATED)
import aiosqlite
import os, json
import contextlib
from typing import Optional, List

DB_PATH = os.getenv("BOT_DB_PATH", "/mnt/data/bot_data.db")

def _pragma_sql():
    return [
        ("PRAGMA journal_mode=WAL;", ()),
        ("PRAGMA synchronous=NORMAL;", ()),
        ("PRAGMA foreign_keys=ON;", ()),
        ("PRAGMA temp_store=MEMORY;", ()),
    ]

@contextlib.asynccontextmanager
async def _connect():
    # shared cache helps when multiple connections exist
    uri = f"file:{DB_PATH}?cache=shared&mode=rwc"
    async with aiosqlite.connect(uri, uri=True, timeout=30.0) as db:
        for sql, args in _pragma_sql():
            await db.execute(sql, args)
        yield db

async def init_db():
    async with _connect() as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_lang(
            user_id INTEGER PRIMARY KEY,
            lang TEXT
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS server_lang(
            guild_id INTEGER PRIMARY KEY,
            lang TEXT
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS translation_channels(
            guild_id INTEGER PRIMARY KEY,
            channels TEXT
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS error_channel(
            guild_id INTEGER PRIMARY KEY,
            channel_id INTEGER
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS bot_emote(
            guild_id INTEGER PRIMARY KEY,
            emote TEXT
        )""")
        await db.commit()

# User language
async def set_user_lang(user_id: int, lang: str) -> None:
    lang = (lang or "").strip().lower()[:16]
    async with _connect() as db:
        await db.execute(
            """INSERT INTO user_lang(user_id, lang)
               VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET lang=excluded.lang""",
            (user_id, lang),
        )
        await db.commit()

async def get_user_lang(user_id: int) -> Optional[str]:
    async with _connect() as db:
        async with db.execute("SELECT lang FROM user_lang WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

# Server default language
async def set_server_lang(guild_id: int, lang: str) -> None:
    lang = (lang or "").strip().lower()[:16]
    async with _connect() as db:
        await db.execute(
            """INSERT INTO server_lang(guild_id, lang)
               VALUES (?, ?)
               ON CONFLICT(guild_id) DO UPDATE SET lang=excluded.lang""",
            (guild_id, lang),
        )
        await db.commit()

async def get_server_lang(guild_id: int) -> Optional[str]:
    async with _connect() as db:
        async with db.execute("SELECT lang FROM server_lang WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

# Translation channels (JSON with CSV back-compat)
async def set_translation_channels(guild_id: int, channels: List[int]) -> None:
    payload = json.dumps([int(c) for c in channels])
    async with _connect() as db:
        await db.execute(
            """INSERT INTO translation_channels(guild_id, channels)
               VALUES (?, ?)
               ON CONFLICT(guild_id) DO UPDATE SET channels=excluded.channels""",
            (guild_id, payload),
        )
        await db.commit()

async def get_translation_channels(guild_id: int) -> List[int]:
    async with _connect() as db:
        async with db.execute("SELECT channels FROM translation_channels WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
            if not row or row[0] is None:
                return []
            raw = row[0]
            try:
                return [int(x) for x in json.loads(raw)]
            except Exception:
                return [int(x) for x in raw.split(",") if x]

# Error channel
async def set_error_channel(guild_id: int, channel_id: Optional[int]) -> None:
    async with _connect() as db:
        await db.execute(
            """INSERT INTO error_channel(guild_id, channel_id)
               VALUES (?, ?)
               ON CONFLICT(guild_id) DO UPDATE SET channel_id=excluded.channel_id""",
            (guild_id, channel_id),
        )
        await db.commit()

async def get_error_channel(guild_id: int) -> Optional[int]:
    async with _connect() as db:
        async with db.execute("SELECT channel_id FROM error_channel WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

# Bot emote
async def set_bot_emote(guild_id: int, emote: str) -> None:
    emote = (emote or "").strip()[:128]
    async with _connect() as db:
        await db.execute(
            """INSERT INTO bot_emote(guild_id, emote)
               VALUES (?, ?)
               ON CONFLICT(guild_id) DO UPDATE SET emote=excluded.emote""",
            (guild_id, emote),
        )
        await db.commit()

async def get_bot_emote(guild_id: int) -> Optional[str]:
    async with _connect() as db:
        async with db.execute("SELECT emote FROM bot_emote WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None