import aiosqlite

DB_PATH = "botdata.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id INTEGER PRIMARY KEY,
            default_lang TEXT,
            error_channel_id INTEGER
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            lang TEXT
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS reaction_channels (
            guild_id INTEGER,
            channel_id INTEGER,
            PRIMARY KEY (guild_id, channel_id)
        )
        """)
        await db.commit()

# Guild settings
async def set_guild_default_lang(guild_id: int, lang: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO guild_settings (guild_id, default_lang)
        VALUES (?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET default_lang=excluded.default_lang
        """, (guild_id, lang))
        await db.commit()

async def get_guild_default_lang(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT default_lang FROM guild_settings WHERE guild_id = ?", (guild_id,))
        row = await cur.fetchone()
        return row[0] if row else None

# User settings
async def set_user_lang(user_id: int, lang: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO user_settings (user_id, lang)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET lang=excluded.lang
        """, (user_id, lang))
        await db.commit()

async def get_user_lang(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT lang FROM user_settings WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row else None

# Reaction channels
async def add_reaction_channel(guild_id: int, channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT OR IGNORE INTO reaction_channels (guild_id, channel_id)
        VALUES (?, ?)
        """, (guild_id, channel_id))
        await db.commit()

async def remove_reaction_channel(guild_id: int, channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM reaction_channels WHERE guild_id=? AND channel_id=?", (guild_id, channel_id))
        await db.commit()

async def get_reaction_channels(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT channel_id FROM reaction_channels WHERE guild_id=?", (guild_id,))
        rows = await cur.fetchall()
        return [r[0] for r in rows]
