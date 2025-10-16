import aiosqlite

DB_PATH = "bot_data.db"

# ...existing tables/functions...

# --- Custom emote ---
async def set_custom_emote(guild_id: int, emoji: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS custom_emote(
            guild_id INTEGER PRIMARY KEY,
            emoji TEXT
        )
        """)
        await db.execute("""
        INSERT INTO custom_emote(guild_id, emoji)
        VALUES (?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET emoji=excluded.emoji
        """, (guild_id, emoji))
        await db.commit()

async def get_custom_emote(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT emoji FROM custom_emote WHERE guild_id=?", (guild_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "🔃"  # default reaction
