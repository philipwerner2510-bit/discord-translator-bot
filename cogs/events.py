# cogs/events.py
import discord
from discord.ext import commands, tasks
from typing import Dict, Tuple
from utils import database
from utils.config import XP_MSG, VOICE_GRANULARITY, VOICE_XP_PER_MIN

class Events(commands.Cog):
    """Message XP and voice-time tracking."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._voice_join: Dict[Tuple[int, int], float] = {}
        self._voice_flush.start()

    def cog_unload(self):
        self._voice_flush.cancel()

    # -- Messages -> XP
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        await database.add_message_xp(message.guild.id, message.author.id, XP_MSG)

    # -- Voice glue
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member,
                                    before: discord.VoiceState, after: discord.VoiceState):
        gid = getattr(member.guild, "id", None)
        if not gid or member.bot:
            return
        key = (gid, member.id)
        now = discord.utils.utcnow().timestamp()

        # Join
        if not before.channel and after.channel:
            self._voice_join[key] = now

        # Leave
        if before.channel and not after.channel:
            start = self._voice_join.pop(key, None)
            if start:
                secs = int(now - start)
                if secs > 0:
                    await database.add_voice_seconds(gid, member.id, secs)
                    if VOICE_XP_PER_MIN > 0:
                        await database.add_message_xp(gid, member.id, VOICE_XP_PER_MIN * max(1, secs // 60))

    @tasks.loop(seconds=VOICE_GRANULARITY)
    async def _voice_flush(self):
        now = discord.utils.utcnow().timestamp()
        # write periodic chunks so progress persists across crashes
        for (gid, uid), start in list(self._voice_join.items()):
            secs = int(now - start)
            if secs >= VOICE_GRANULARITY:
                await database.add_voice_seconds(gid, uid, VOICE_GRANULARITY)
                self._voice_join[(gid, uid)] = start + VOICE_GRANULARITY

async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))
