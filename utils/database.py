import aiosqlite

DB_PATH = "bot_data.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_lang(user_id INTEGER PRIMARY KEY, lang TEXT)
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS server_lang(guild_id INTEGER PRIMARY KEY, lang TEXT)
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS translation_channels(guild_id INTEGER PRIMARY KEY, channels TEXT)
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS error_channel(guild_id INTEGER PRIMARY KEY, channel_id INTEGER)
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS server_emote(guild_id INTEGER PRIMARY KEY, emote TEXT)
        """)
        await db.commit()

# --- User ---
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

# --- Server ---
