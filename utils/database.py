import aiosqlite
import os
from datetime import datetime, timezone

DB_PATH = os.getenv("BOT_DB_PATH", "/mnt/data/bot_data.db")

async def _ensure_migrations(db: aiosqlite.Connection):
    # Add missing columns without breaking existing data
    async with db.execute("PRAGMA table_info(ai_usage)") as cur:
        cols = [r[1] for r in await cur.fetchall()]  # name is index 1
    if cols:
        if "eur" not in cols:
            try:
                await db.execute("ALTER TABLE ai_usage ADD COLUMN eur REAL NOT NULL DEFAULT 0.0")
                await db.commit()
            except Exception:
                pass
        if "tokens" not in cols:
            try:
                await db.execute("ALTER TABLE ai_usage ADD COLUMN tokens INTEGER NOT NULL DEFAULT 0")
                await db.commit()
            except Exception:
                pass

    async with db.execute("PRAGMA table_info(guild_ai)") as cur:
        cols = [r[1] for r in await cur.fetchall()]
    if cols and "enabled" not in cols:
        try:
            await db.execute("ALTER TABLE guild_ai ADD COLUMN enabled INTEGER NOT NULL DEFAULT 1")
            await db.commit()
        except Exception:
            pass

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
        await db.execute("""CREATE TABLE IF NOT EXISTS ai_usage(
            month TEXT PRIMARY KEY, tokens INTEGER NOT NULL DEFAULT 0, eur REAL NOT NULL DEFAULT 0.0)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS user_stats(
            user_id INTEGER PRIMARY KEY, translations INTEGER NOT NULL DEFAULT 0)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS guild_ai(
            guild_id INTEGER PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 1)""")
        await db.commit()

        # 🔧 Run lightweight migrations to add any missing columns
        await _ensure_migrations(db)

# ---------- helpers (cursor-style) ----------
async def set_user_lang(user_id: int, lang: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO user_lang(user_id, lang) VALUES(?,?)
        ON CONFLICT(user_id) DO UPDATE SET lang=excluded.lang
        """, (user_id, lang))
        await db.commit()

async def get_user_lang(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT lang FROM user_lang WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

async def set_server_lang(guild_id: int, lang: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO server_lang(guild_id, lang) VALUES(?,?)
        ON CONFLICT(guild_id) DO UPDATE SET lang=excluded.lang
        """, (guild_id, lang))
        await db.commit()

async def get_server_lang(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT lang FROM server_lang WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

async def set_translation_channels(guild_id: int, channels: list[int]):
    channels_str = ",".join(map(str, channels))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO translation_channels(guild_id, channels) VALUES(?,?)
        ON CONFLICT(guild_id) DO UPDATE SET channels=excluded.channels
        """, (guild_id, channels_str))
        await db.commit()

async def get_translation_channels(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT channels FROM translation_channels WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
            if row and row[0]:
                return [int(x) for x in row[0].split(",") if x.strip()]
            return []

async def set_error_channel(guild_id: int, channel_id: int | None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO error_channel(guild_id, channel_id) VALUES(?,?)
        ON CONFLICT(guild_id) DO UPDATE SET channel_id=excluded.channel_id
        """, (guild_id, channel_id))
        await db.commit()

async def get_error_channel(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT channel_id FROM error_channel WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

async def set_bot_emote(guild_id: int, emote: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO bot_emote(guild_id, emote) VALUES(?,?)
        ON CONFLICT(guild_id) DO UPDATE SET emote=excluded.emote
        """, (guild_id, emote))
        await db.commit()

async def get_bot_emote(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT emote FROM bot_emote WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

# ---------- AI usage ----------
def _month_key() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m")

async def add_ai_usage(tokens: int, eur: float):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            mk = _month_key()
            await db.execute("""
            INSERT INTO ai_usage(month, tokens, eur) VALUES(?,?,?)
            ON CONFLICT(month) DO UPDATE SET
                tokens = tokens + excluded.tokens,
                eur    = eur    + excluded.eur
            """, (mk, tokens, eur))
            await db.commit()
    except Exception:
        pass

async def get_current_ai_usage():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT tokens, eur FROM ai_usage WHERE month=?", (_month_key(),)) as cur:
            row = await cur.fetchone()
            if row:
                return int(row[0] or 0), float(row[1] or 0.0)
            return 0, 0.0

# ---------- Guild AI toggle ----------
async def set_ai_enabled(guild_id: int, enabled: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO guild_ai(guild_id, enabled) VALUES(?,?)
        ON CONFLICT(guild_id) DO UPDATE SET enabled=excluded.enabled
        """, (guild_id, 1 if enabled else 0))
        await db.commit()

async def get_ai_enabled(guild_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT enabled FROM guild_ai WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
            return bool(row[0]) if row else True

# ---------- User stats ----------
async def inc_user_translation(user_id: int, delta: int = 1):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
            INSERT INTO user_stats(user_id, translations) VALUES(?,?)
            ON CONFLICT(user_id) DO UPDATE SET translations = translations + ?
            """, (user_id, delta, delta))
            await db.commit()
    except Exception:
        pass

async def top_translators(limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, translations FROM user_stats ORDER BY translations DESC LIMIT ?",
            (limit,)
        ) as cur:
            rows = await cur.fetchall()
            return [(int(r[0]), int(r[1])) for r in rows]