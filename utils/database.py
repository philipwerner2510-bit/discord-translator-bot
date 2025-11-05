# utils/database.py
import aiosqlite
import os
from datetime import datetime

DB_PATH = os.getenv("BOT_DB_PATH", "/mnt/data/bot_data.db")

# pricing (EUR) per 1k tokens (adjust as you wish)
PRICE_IN = float(os.getenv("AI_PRICE_IN_EUR_PER_1K", "0.00015"))
PRICE_OUT = float(os.getenv("AI_PRICE_OUT_EUR_PER_1K", "0.00060"))

# ---------- init ----------
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS user_lang(
            user_id INTEGER PRIMARY KEY,
            lang TEXT
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS server_lang(
            guild_id INTEGER PRIMARY KEY,
            lang TEXT
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS translation_channels(
            guild_id INTEGER PRIMARY KEY,
            channels TEXT
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS error_channel(
            guild_id INTEGER PRIMARY KEY,
            channel_id INTEGER
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS bot_emote(
            guild_id INTEGER PRIMARY KEY,
            emote TEXT
        )""")
        # persistent translation counters
        await db.execute("""CREATE TABLE IF NOT EXISTS translation_counters(
            id INTEGER PRIMARY KEY CHECK (id=1),
            total INTEGER NOT NULL DEFAULT 0,
            last_daily_key TEXT
        )""")
        await db.execute("""INSERT OR IGNORE INTO translation_counters(id,total,last_daily_key) VALUES(1,0,NULL)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS translation_daily(
            day TEXT PRIMARY KEY,
            count INTEGER NOT NULL DEFAULT 0
        )""")
        # AI usage aggregation per month
        await db.execute("""CREATE TABLE IF NOT EXISTS ai_usage_month(
            month TEXT PRIMARY KEY,
            tokens_in INTEGER NOT NULL DEFAULT 0,
            tokens_out INTEGER NOT NULL DEFAULT 0
        )""")
        await db.commit()

# ---------- helpers ----------
def _day_key():
    return datetime.utcnow().strftime("%Y-%m-%d")

def _month_key():
    return datetime.utcnow().strftime("%Y-%m")

# ---------- languages ----------
async def set_user_lang(user_id: int, lang: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""INSERT INTO user_lang(user_id, lang)
            VALUES(?,?)
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
        await db.execute("""INSERT INTO server_lang(guild_id, lang)
            VALUES(?,?)
            ON CONFLICT(guild_id) DO UPDATE SET lang=excluded.lang
        """, (guild_id, lang))
        await db.commit()

async def get_server_lang(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT lang FROM server_lang WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

# ---------- channels ----------
async def set_translation_channels(guild_id: int, channels: list[int]):
    s = ",".join(map(str, channels))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""INSERT INTO translation_channels(guild_id, channels)
            VALUES(?,?)
            ON CONFLICT(guild_id) DO UPDATE SET channels=excluded.channels
        """, (guild_id, s))
        await db.commit()

async def get_translation_channels(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT channels FROM translation_channels WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
            if not row or not row[0]:
                return []
            return [int(x) for x in row[0].split(",") if x]

# ---------- error channel ----------
async def set_error_channel(guild_id: int, channel_id: int | None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""INSERT INTO error_channel(guild_id, channel_id)
            VALUES(?,?)
            ON CONFLICT(guild_id) DO UPDATE SET channel_id=excluded.channel_id
        """, (guild_id, channel_id))
        await db.commit()

async def get_error_channel(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT channel_id FROM error_channel WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

# ---------- bot emote ----------
async def set_bot_emote(guild_id: int, emote: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""INSERT INTO bot_emote(guild_id, emote)
            VALUES(?,?)
            ON CONFLICT(guild_id) DO UPDATE SET emote=excluded.emote
        """, (guild_id, emote))
        await db.commit()

async def get_bot_emote(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT emote FROM bot_emote WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

# ---------- stats (persistent) ----------
async def add_translation_stat(guild_id: int, user_id: int, used_ai: bool, tokens_in: int=0, tokens_out: int=0):
    async with aiosqlite.connect(DB_PATH) as db:
        # update totals & daily
        day = _day_key()
        # total
        await db.execute("UPDATE translation_counters SET total = total + 1 WHERE id=1")
        # daily upsert
        await db.execute("""INSERT INTO translation_daily(day, count)
            VALUES(?,1)
            ON CONFLICT(day) DO UPDATE SET count=count+1
        """, (day,))

        # ai usage by month
        month = _month_key()
        await db.execute("""INSERT INTO ai_usage_month(month, tokens_in, tokens_out)
            VALUES(?,?,?)
            ON CONFLICT(month) DO UPDATE SET
                tokens_in = tokens_in + excluded.tokens_in,
                tokens_out = tokens_out + excluded.tokens_out
        """, (month, tokens_in, tokens_out))
        await db.commit()

async def get_translation_totals():
    async with aiosqlite.connect(DB_PATH) as db:
        # total
        async with db.execute("SELECT total FROM translation_counters WHERE id=1") as cur:
            row = await cur.fetchone()
            total = int(row[0]) if row else 0
        # daily
        async with db.execute("SELECT count FROM translation_daily WHERE day=?", (_day_key(),)) as cur:
            row = await cur.fetchone()
            daily = int(row[0]) if row else 0
        return daily, total

async def get_month_ai_usage():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT tokens_in, tokens_out FROM ai_usage_month WHERE month=?", (_month_key(),)) as cur:
            row = await cur.fetchone()
            ti = int(row[0]) if row else 0
            to = int(row[1]) if row else 0
        # estimated EUR (1k token pricing)
        eur = (ti/1000.0)*PRICE_IN + (to/1000.0)*PRICE_OUT
        return ti, to, eur