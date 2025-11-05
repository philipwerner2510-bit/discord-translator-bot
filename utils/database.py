import aiosqlite, os, datetime

DB_PATH = os.getenv("BOT_DB_PATH", "./bot_data.db")

async def init():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS user_lang(user_id INTEGER PRIMARY KEY, lang TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS server_lang(guild_id INTEGER PRIMARY KEY, lang TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS translation_channels(guild_id INTEGER PRIMARY KEY, channels TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS error_channel(guild_id INTEGER PRIMARY KEY, channel_id INTEGER)")
        await db.execute("CREATE TABLE IF NOT EXISTS bot_emote(guild_id INTEGER PRIMARY KEY, emote TEXT)")
        await db.execute("""CREATE TABLE IF NOT EXISTS stats(
            guild_id INTEGER, user_id INTEGER, count INTEGER DEFAULT 0,
            PRIMARY KEY(guild_id, user_id))""")
        await db.commit()

async def set_user_lang(uid:int, lang:str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO user_lang(user_id,lang) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET lang=excluded.lang", (uid,lang))
        await db.commit()

async def get_user_lang(uid:int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT lang FROM user_lang WHERE user_id=?", (uid,))
        r = await cur.fetchone()
        return r[0] if r else None

async def set_server_lang(gid:int, lang:str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO server_lang(guild_id,lang) VALUES(?,?) ON CONFLICT(guild_id) DO UPDATE SET lang=excluded.lang", (gid,lang))
        await db.commit()

async def get_server_lang(gid:int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT lang FROM server_lang WHERE guild_id=?", (gid,))
        r = await cur.fetchone()
        return r[0] if r else None

async def set_translation_channels(gid:int, channels:list[int]):
    s = ",".join(map(str, channels))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO translation_channels(guild_id,channels) VALUES(?,?) ON CONFLICT(guild_id) DO UPDATE SET channels=excluded.channels", (gid,s))
        await db.commit()

async def get_translation_channels(gid:int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT channels FROM translation_channels WHERE guild_id=?", (gid,))
        r = await cur.fetchone()
        if not r or not r[0]: return []
        return [int(x) for x in r[0].split(",") if x.strip()]

async def set_error_channel(gid:int, ch_id:int|None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO error_channel(guild_id,channel_id) VALUES(?,?) ON CONFLICT(guild_id) DO UPDATE SET channel_id=excluded.channel_id", (gid,ch_id))
        await db.commit()

async def get_error_channel(gid:int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT channel_id FROM error_channel WHERE guild_id=?", (gid,))
        r = await cur.fetchone()
        return r[0] if r else None

async def set_bot_emote(gid:int, emote:str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO bot_emote(guild_id,emote) VALUES(?,?) ON CONFLICT(guild_id) DO UPDATE SET emote=excluded.emote", (gid, emote))
        await db.commit()

async def get_bot_emote(gid:int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT emote FROM bot_emote WHERE guild_id=?", (gid,))
        r = await cur.fetchone()
        return r[0] if r else None

async def add_translation_stat(gid:int, uid:int, used_ai:bool=True, tokens_in:int=0, tokens_out:int=0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""INSERT INTO stats(guild_id,user_id,count)
                            VALUES(?,?,1) ON CONFLICT(guild_id,user_id)
                            DO UPDATE SET count=count+1""", (gid, uid))
        await db.commit()

async def get_leaderboard(gid:int, limit:int=10):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id, count FROM stats WHERE guild_id=? ORDER BY count DESC LIMIT ?", (gid, limit))
        return await cur.fetchall()
