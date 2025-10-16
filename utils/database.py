import aiosqlite

DB_PATH = "bot_data.db"

# -----------------------
# Initialize DB
# -----------------------
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
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
        async with db.execute("SELECT lang FROM user_lang WHERE user_id=?", (user_id,)) as cursor:
            row = await cursor.fetchone()
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
        async with db.execute("SELECT lang FROM server_lang WHERE guild_id=?", (guild_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

# -----------------------
# Translation channels
# -----------------------
async def set_translation_channels(guild_id: int, channels: list):
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
        async with db.execute("SELECT channels FROM translation_channels WHERE guild_id=?", (guild_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
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
        async with db.execute("SELECT channel_id FROM error_channel WHERE guild_id=?", (guild_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

# -----------------------
# Bot emote (new)
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
        async with db.execute("SELECT emote FROM bot_emote WHERE guild_id=?", (guild_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None
