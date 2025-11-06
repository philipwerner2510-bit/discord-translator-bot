# cogs/events.py
import discord
from discord.ext import commands, tasks
from typing import Dict, Tuple
from utils import database
from utils.config import XP_MSG, VOICE_GRANULARITY, VOICE_XP_PER_MIN

class Events(commands.Cog):
    """Core events: message XP & voice tracking."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # cache (guild_id, user_id) -> joined_at_ts
        self._voice_join: Dict[Tuple[int, int], float] = {}
        self._flush_voice_loop.start()

    def cog_unload(self):
        self._flush_voice_loop.cancel()

    # -------- Messages -> XP --------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        # award per message
        await database.add_message_xp(message.guild.id, message.author.id, XP_MSG)

    # -------- Voice join/leave tracking --------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member,
                                    before: discord.VoiceState, after: discord.VoiceState):
        gid = getattr(member.guild, "id", None)
        if not gid or member.bot:
            return

        key = (gid, member.id)

        # Joined voice
        if not before.channel and after.channel:
            self._voice_join[key] = discord.utils.utcnow().timestamp()

        # Left voice
        if before.channel and not after.channel:
            start = self._voice_join.pop(key, None)
            if start:
                secs = int(discord.utils.utcnow().timestamp() - start)
                if secs > 0:
                    await database.add_voice_seconds(gid, member.id, secs)
                    # Optional: convert to XP per minute
                    if VOICE_XP_PER_MIN > 0:
                        mins = max(1, secs // 60)
                        await database.add_message_xp(gid, member.id, VOICE_XP_PER_MIN * mins)

        # Switch channels: treat as continuous, no write needed

    # Safety flush for users stuck in cache (every N seconds)
    @tasks.loop(seconds=VOICE_GRANULARITY)
    async def _flush_voice_loop(self):
        now = discord.utils.utcnow().timestamp()
        # We can’t iterate guild members here reliably; just write partial increments
        stale = list(self._voice_join.items())
        for (gid, uid), start in stale:
            secs = int(now - start)
            if secs >= VOICE_GRANULARITY:
                # write chunk and move start forward
                await database.add_voice_seconds(gid, uid, VOICE_GRANULARITY)
                self._voice_join[(gid, uid)] = start + VOICE_GRANULARITY

async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))
