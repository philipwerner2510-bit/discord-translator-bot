# cogs/xp_system.py
from __future__ import annotations
import asyncio, time, math
import discord
from discord.ext import commands
from discord import app_commands
from utils.brand import COLOR, footer
from utils import database

# ====== Tuning knobs ======
XP_MSG            = 5        # per eligible message
XP_TRANSLATION    = 10       # per successful translation (manual or reaction)
XP_VOICE_PER_MIN  = 2        # every full minute in VC
MSG_MIN_CHARS     = 5        # ignore tiny messages
MSG_COOLDOWN_S    = 10       # per-user cooldown for message XP
MSG_DUP_WINDOW_S  = 45       # ignore duplicate content within this window
LEADERBOARD_PAGE  = 10       # entries per page
LEVEL_ROLE_STEP   = 5        # role every N levels (used by /xp roles setup)
LEVEL_COLOR_HEX   = [0x00E6F6, 0x10D3F0, 0x20C0EA, 0x30ADE4, 0x409ADF, 0x5086D9, 0x6073D3, 0x7050CD, 0x803DC7, 0x902AC1]

# ====== Level curve ======
def level_from_xp(xp:int)->int:
    # Smooth quadratic-ish: XP needed to reach level n ≈ 100*n*(n+1)/2
    # Solve n from xp ≈ 50n(n+1)
    # Analytical approx:
    return max(1, int((math.sqrt(1 + (xp/50)*4) - 1) / 2) + 1)

def xp_for_level(level:int)->int:
    # XP *to reach* this level (floor)
    return 50 * (level-1) * level

def progress(xp:int)->tuple[int,int,int]:
    lvl = level_from_xp(xp)
    cur = xp - xp_for_level(lvl)
    nxt = xp_for_level(lvl+1) - xp_for_level(lvl)
    return lvl, cur, nxt

# ====== Cog ======
class XpSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_msg: dict[tuple[int,int], tuple[float,str]] = {}  # (gid,uid) -> (ts, hash)
        self._msg_cd:   dict[tuple[int,int], float] = {}             # (gid,uid) -> last ts
        self._voice_join: dict[tuple[int,int], float] = {}           # (gid,uid) -> join ts

    # --- message activity ---
    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        if not m.guild or m.author.bot:
            return
        if len(m.content.strip()) < MSG_MIN_CHARS:
            return

        gid, uid = m.guild.id, m.author.id
        now = time.time()
        key = (gid, uid)

        # cooldown
        last = self._msg_cd.get(key, 0)
        if now - last < MSG_COOLDOWN_S:
            return

        # duplicate within window
        content_key = m.content.strip().lower()
        prev = self._last_msg.get(key)
        if prev and (now - prev[0] < MSG_DUP_WINDOW_S) and prev[1] == content_key:
            return

        # passed filters → award
        self._msg_cd[key] = now
        self._last_msg[key] = (now, content_key)

        try:
            await database.add_activity(gid, uid, xp=XP_MSG, messages=1)
        except Exception:
            pass

    # --- voice activity ---
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot or not member.guild:
            return
        gid, uid = member.guild.id, member.id
        key = (gid, uid)

        # Joined a channel
        if not before.channel and after.channel:
            self._voice_join[key] = time.time()
            return

        # Left channel or switched channels
        if before.channel and not after.channel or (before.channel and after.channel and before.channel.id != after.channel.id):
            start = self._voice_join.pop(key, None)
            if start:
                delta = max(0, int(time.time() - start))
                if delta >= 60:
                    minutes = delta // 60
                    try:
                        await database.add_activity(gid, uid, xp=minutes * XP_VOICE_PER_MIN, voice_seconds=delta)
                    except Exception:
                        pass

    # -------- Commands group --------
    xp = app_commands.Group(name="xp", description="Activity & leveling")

    @xp.command(name="profile", description="Show XP profile (level, progress, counters).")
    async def xp_profile(self, it: discord.Interaction, user: discord.User | None = None):
        await it.response.defer()
        user = user or it.user
        gid = it.guild.id if it.guild else None
        xp, msgs, trans, vsec = await database.get_xp(gid, user.id)
        lvl, cur, need = progress(xp)

        bar_len = 20
        filled = int((cur / max(1, need)) * bar_len)
        bar = "▰" * filled + "▱" * (bar_len - filled)

        desc = (
            f"**Level {lvl}** — **{xp} XP**\n"
            f"`{bar}`  **{cur}/{need}** to next\n\n"
            f"**Messages:** {msgs} • **Translations:** {trans} • **Voice:** {vsec//60} min"
        )
        e = discord.Embed(title=f"{user.display_name}", description=desc, color=COLOR)
        e.set_footer(text=footer())
        e.set_thumbnail(url=user.display_avatar.url)
        await it.followup.send(embed=e)

    @xp.command(name="leaderboard", description="Top XP members in this server.")
    async def xp_leaderboard(self, it: discord.Interaction, page: int = 1):
        await it.response.defer()
        gid = it.guild.id if it.guild else None
        page = max(1, page)
        offset = (page - 1) * LEADERBOARD_PAGE
        rows = await database.get_xp_leaderboard(gid, LEADERBOARD_PAGE, offset)
        if not rows:
            return await it.followup.send("No activity yet. Start chatting, translating, or talking in voice!")

        lines = []
        start_idx = offset + 1
        medal = {0:"🥇",1:"🥈",2:"🥉"}
        for idx, (uid, xp, msgs, trans, vsec) in enumerate(rows):
            m = it.guild.get_member(uid) or f"<@{uid}>"
            lvl = level_from_xp(xp)
            icon = medal.get(idx, f"#{start_idx+idx}")
            lines.append(f"**{icon}** {getattr(m, 'display_name', m)} — **Lv {lvl}** • **{xp} XP**")

        e = discord.Embed(title="🏆 Activity Leaderboard", description="\n".join(lines), color=COLOR)
        e.set_footer(text=f"{footer()} • Page {page}")
        await it.followup.send(embed=e)

    # ---- Level roles management ----
    @xp.command(name="roles", description="Create or update level roles (admin).")
    @app_commands.describe(step="Create a role every N levels (default 5)", count="How many roles to create (default 10)")
    @app_commands.checks.has_permissions(administrator=True)
    async def xp_roles(self, it: discord.Interaction, step: int = LEVEL_ROLE_STEP, count: int = 10):
        await it.response.defer(ephemeral=True)
        guild = it.guild
        created = 0
        for i in range(count):
            lvl = (i+1) * step
            name = f"Lv {lvl}+"
            color = discord.Color(LEVEL_COLOR_HEX[i % len(LEVEL_COLOR_HEX)])
            role = discord.utils.get(guild.roles, name=name)
            try:
                if role:
                    await role.edit(color=color, reason="Zephyra level role refresh")
                else:
                    await guild.create_role(name=name, color=color, reason="Zephyra level roles")
                    created += 1
            except Exception:
                pass
        await it.followup.send(f"Level roles ready. Created: {created}, updated: {count - created}.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(XpSystem(bot))
