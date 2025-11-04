import aiosqlite
import os
import datetime

# Use environment variable for Koyeb, fallback to /mnt/data/bot_data.db
DB_PATH = os.getenv("BOT_DB_PATH", "/mnt/data/bot_data.db")

# -----------------------
# Helpers
# -----------------------
def _current_month_key() -> str:
    # YYYY-MM for monthly aggregation
    now = datetime.datetime.utcnow()
    return f"{now.year:04d}-{now.month:02d}"

async def _column_exists(db: aiosqlite.Connection, table: str, column: str) -> bool:
    try:
        async with db.execute(f"PRAGMA table_info({table})") as cur:
            rows = await cur.fetchall()
            return any(r[1] == column for r in rows)  # r[1] = name
    except Exception:
        return False


# -----------------------
# Initialize / migrate DB
# -----------------------
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # base tables (from your original schema)
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

        # NEW: per-guild AI toggle
        await db.execute("""
        CREATE TABLE IF NOT EXISTS ai_settings(
            guild_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 1
        )
        """)

        # NEW: monthly AI usage (global aggregation for billing)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS ai_usage_monthly(
            month TEXT PRIMARY KEY,
            tokens INTEGER DEFAULT 0,
            cost REAL DEFAULT 0.0
        )
        """)

        # (Optional) migrate: add ai_enabled column to server_lang if someone used older builds
        # Not strictly needed now that ai_settings exists; kept for compatibility.
        if await _column_exists(db, "server_lang", "ai_enabled") is False:
            try:
                await db.execute("ALTER TABLE server_lang ADD COLUMN ai_enabled INTEGER DEFAULT 1")
            except Exception:
                pass

        await db.commit()


# -----------------------
# User language
# -----------------------
async def set_user_lang(user_id: int, lang: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO user_lang(user_id, lang)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET lang=excluded.lang
        """, (user_id, lang))
        await db.commit()

async def get_user_lang(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT lang FROM user_lang WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


# -----------------------
# Server default language
# -----------------------
async def set_server_lang(guild_id: int, lang: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO server_lang(guild_id, lang)
        VALUES (?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET lang=excluded.lang
        """, (guild_id, lang))
        await db.commit()

async def get_server_lang(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT lang FROM server_lang WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


# -----------------------
# Translation channels
# -----------------------
async def set_translation_channels(guild_id: int, channels: list[int]):
    channels_str = ",".join(map(str, channels))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO translation_channels(guild_id, channels)
        VALUES (?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET channels=excluded.channels
        """, (guild_id, channels_str))
        await db.commit()

async def get_translation_channels(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT channels FROM translation_channels WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
            if row and row[0]:
                return [int(x) for x in row[0].split(",") if x]
            return []


# -----------------------
# Error channel
# -----------------------
async def set_error_channel(guild_id: int, channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO error_channel(guild_id, channel_id)
        VALUES (?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET channel_id=excluded.channel_id
        """, (guild_id, channel_id))
        await db.commit()

async def get_error_channel(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT channel_id FROM error_channel WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


# -----------------------
# Bot emote
# -----------------------
async def set_bot_emote(guild_id: int, emote: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO bot_emote(guild_id, emote)
        VALUES (?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET emote=excluded.emote
        """, (guild_id, emote))
        await db.commit()

async def get_bot_emote(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT emote FROM bot_emote WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


# -----------------------
# AI settings per guild
# -----------------------
async def set_ai_enabled(guild_id: int, enabled: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO ai_settings(guild_id, enabled)
        VALUES (?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET enabled=excluded.enabled
        """, (guild_id, 1 if enabled else 0))
        await db.commit()

async def get_ai_enabled(guild_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT enabled FROM ai_settings WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
            if row is None:
                # default ON if not set
                return True
            return bool(row[0])


# -----------------------
# AI usage accounting (monthly, global)
# -----------------------
async def add_ai_usage(tokens: int, cost_eur: float):
    """Accumulate usage into the current month (global, not per-guild)."""
    month = _current_month_key()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO ai_usage_monthly(month, tokens, cost)
        VALUES (?, ?, ?)
        ON CONFLICT(month) DO UPDATE SET
            tokens = ai_usage_monthly.tokens + excluded.tokens,
            cost   = ai_usage_monthly.cost   + excluded.cost
        """, (month, int(tokens), float(cost_eur)))
        await db.commit()

async def get_current_ai_usage() -> tuple[int, float]:
    """Return (tokens, cost_eur) for the current month."""
    month = _current_month_key()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT tokens, cost FROM ai_usage_monthly WHERE month=?", (month,)) as cur:
            row = await cur.fetchone()
            if not row:
                return 0, 0.0
            return int(row[0] or 0), float(row[1] or 0.0)