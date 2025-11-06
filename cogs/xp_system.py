# cogs/xp_system.py
from __future__ import annotations
import asyncio, time
import math
import typing as T

import discord
from discord.ext import commands
from discord import app_commands

from utils.brand import COLOR, footer
from utils import database

# =========================
#        TUNING
# =========================
# Balanced amounts (your preference):
XP_MSG                = 3      # per eligible message (with anti-spam)
XP_TRANSLATION        = 9      # each successful translation (manual or reaction)
XP_VOICE_PER_MIN      = 2      # per full minute in voice
XP_SLASH              = 3      # each successful slash command (except blacklisted)

# Anti-spam for messages:
MSG_MIN_CHARS         = 5      # ignore tiny messages like "A"
MSG_COOLDOWN_S        = 10     # per-user cooldown between earning message XP
MSG_DUP_WINDOW_S      = 45     # ignore duplicate content within this time window

# Leaderboard & roles:
LEADERBOARD_PAGE      = 10     # entries per page
LEVEL_ROLE_STEP       = 5      # create/apply a role every N levels
# Zephyra-themed gradient (light blue → cyan → purple):
LEVEL_COLOR_HEX       = [0xB4F1FF, 0x7EE8FF, 0x48DBFF, 0x18CDF7, 0x00BEEA,
                         0x00A6E0, 0x5C8AE1, 0x7B6BE7, 0x8B55EB, 0x9B5CFF]

# =========================
#      LEVEL CURVE
# =========================
# Smooth RPG curve (Option B):
# XP needed to go from level n → n+1:  5*n^2 + 50*n
def xp_to_next(level: int) -> int:
    return 5 * (level ** 2) + 50 * level

def level_progress(total_xp: int) -> tuple[int, int, int]:
    """Return (level, cur_into_level, needed_for_next)."""
    level = 1
    remain = max(0, total_xp)
    while True:
        need = xp_to_next(level)
        if remain < need:
            return level, remain, need
        remain -= need
        level += 1

def highest_qualified_level(total_xp: int) -> int:
    lvl, cur, need = level_progress(total_xp)
    return lvl

# =========================
#    INTERNAL HELPERS
# =========================
def _is_level_role(role: discord.Role) -> bool:
    # Generic naming, no Zephyra branding: "Level X+"
    return role.name.startswith("Level ") and role.name.endswith("+")

def _role_threshold(role: discord.Role) -> int | None:
    # Parse "Level {lvl}+"
    try:
        mid = role.name[len("Level "): -1].strip()
        return int(mid)
    except Exception:
        return None

async def _grant_xp_and_maybe_roles(
    cog: "XpSystem",
    member: discord.Member,
    delta_xp: int = 0,
    messages: int = 0,
    translations: int = 0,
    voice_seconds: int = 0,
):
    gid, uid = member.guild.id, member.id
    # Update DB
    await database.add_activity(
        gid, uid,
        xp=delta_xp,
        messages=messages,
        translations=translations,
        voice_seconds=voice_seconds
    )
    # Then adjust roles
    await cog._ensure_best_level_role(member)

# =========================
#          COG
# =========================
class XpSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_msg: dict[tuple[int,int], tuple[float,str]] = {}  # (gid,uid) -> (ts, normalized_content)
        self._msg_cd:   dict[tuple[int,int], float] = {}             # (gid,uid) -> last earn ts
        self._voice_join: dict[tuple[int,int], float] = {}           # (gid,uid) -> join timestamp

    # ===== Message XP with anti-spam =====
    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        if not m.guild or m.author.bot:
            return
        content = (m.content or "").strip()
        if len(content) < MSG_MIN_CHARS:
            return

        gid, uid = m.guild.id, m.author.id
        now = time.time()
        key = (gid, uid)

        # cooldown
        last = self._msg_cd.get(key, 0.0)
        if now - last < MSG_COOLDOWN_S:
            return

        # duplicate within window
        normalized = content.lower()
        prev = self._last_msg.get(key)
        if prev and (now - prev[0] < MSG_DUP_WINDOW_S) and prev[1] == normalized:
            return

        # Accept → record & grant
        self._msg_cd[key] = now
        self._last_msg[key] = (now, normalized)

        try:
            await _grant_xp_and_maybe_roles(self, m.author, delta_xp=XP_MSG, messages=1)
        except Exception:
            pass

    # ===== Voice XP (join/leave accounting) =====
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member,
                                    before: discord.VoiceState, after: discord.VoiceState):
        if member.bot or not member.guild:
            return
        gid, uid = member.guild.id, member.id
        key = (gid, uid)

        # Joined a channel
        if not before.channel and after.channel:
            self._voice_join[key] = time.time()
            return

        # Left channel or switched channels
        if before.channel and (not after.channel or before.channel.id != after.channel.id):
            start = self._voice_join.pop(key, None)
            if start:
                delta = max(0, int(time.time() - start))
                if delta >= 60:
                    minutes = delta // 60
                    try:
                        await _grant_xp_and_maybe_roles(
                            self, member,
                            delta_xp=minutes * XP_VOICE_PER_MIN,
                            voice_seconds=delta
                        )
                    except Exception:
                        pass

    # ===== Slash command XP (except blacklisted groups) =====
    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction: discord.Interaction, command: app_commands.Command):
        try:
            if not interaction.guild or interaction.user.bot:
                return
            # Avoid awarding XP for management/admin commands that could be spammed
            qname = getattr(command, "qualified_name", command.name)  # e.g., "ops sync", "xp profile"
            lowered = qname.lower()
            blacklist_prefixes = ("ops", "owner")  # admin/owner tools
            if lowered.startswith(blacklist_prefixes):
                return
            # Don't farm within xp group itself except profile/leaderboard are fine?
            # We'll allow /xp profile and /xp leaderboard to give XP too (small amount)
            member = interaction.guild.get_member(interaction.user.id)
            if not member:
                return
            await _grant_xp_and_maybe_roles(self, member, delta_xp=XP_SLASH)
        except Exception:
            pass

    # ===== React to translation XP events (emitted by translate.py) =====
    @commands.Cog.listener()
    async def on_xp_gain(self, guild_id: int, user_id: int):
        """translate.py dispatches this after awarding translation XP so we can update roles immediately."""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return
            member = guild.get_member(user_id)
            if not member:
                return
            await self._ensure_best_level_role(member)
        except Exception:
            pass

    # ===== XP Commands =====
    xp = app_commands.Group(name="xp", description="Activity & leveling")

    @xp.command(name="profile", description="Show XP profile (level, progress, counters).")
    async def xp_profile(self, it: discord.Interaction, user: discord.User | None = None):
        await it.response.defer()
        user = user or it.user
        gid = it.guild.id if it.guild else None
        xp, msgs, trans, vsec = await database.get_xp(gid, user.id)
        lvl, cur, need = level_progress(xp)

        bar_len = 22
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
            lvl = highest_qualified_level(xp)
            icon = medal.get(idx, f"#{start_idx+idx}")
            lines.append(f"**{icon}** {getattr(m, 'display_name', m)} — **Lv {lvl}** • **{xp} XP**")

        e = discord.Embed(title="🏆 Activity Leaderboard", description="\n".join(lines), color=COLOR)
        e.set_footer(text=f"{footer()} • Page {page}")
        await it.followup.send(embed=e)

    # ---- Level roles management: create/update ----
    @xp.command(name="roles_setup", description="Create or refresh level roles (admin).")
    @app_commands.describe(step="Create a role every N levels (default 5)", count="How many tiers to prepare (default 10)")
    @app_commands.checks.has_permissions(administrator=True)
    async def xp_roles_setup(self, it: discord.Interaction, step: int = LEVEL_ROLE_STEP, count: int = 10):
        await it.response.defer(ephemeral=True)
        guild = it.guild
        created = 0
        updated = 0
        for i in range(count):
            lvl = (i+1) * step
            name = f"Level {lvl}+"
            color = discord.Color(LEVEL_COLOR_HEX[i % len(LEVEL_COLOR_HEX)])
            role = discord.utils.get(guild.roles, name=name)
            try:
                if role:
                    await role.edit(color=color, reason="Level role refresh")
                    updated += 1
                else:
                    await guild.create_role(name=name, color=color, reason="Create level role")
                    created += 1
            except Exception:
                pass
        await it.followup.send(f"Level roles ready. Created: {created}, updated: {updated}.", ephemeral=True)

    # ---- Force re-check and assign best role to a user/admin ----
    @xp.command(name="roles_apply", description="Re-apply the best level role to a member (admin).")
    @app_commands.checks.has_permissions(administrator=True)
    async def xp_roles_apply(self, it: discord.Interaction, member: discord.Member | None = None):
        await it.response.defer(ephemeral=True)
        member = member or it.user
        try:
            await self._ensure_best_level_role(member)
            await it.followup.send(f"Applied best level role to {member.mention}.", ephemeral=True)
        except Exception as e:
            await it.followup.send(f"Failed: {e}", ephemeral=True)

    # ===== Role assignment core =====
    async def _ensure_best_level_role(self, member: discord.Member):
        guild = member.guild
        total_xp, *_ = await database.get_xp(guild.id, member.id)
        lvl = highest_qualified_level(total_xp)

        # Find all level roles and sort by threshold
        level_roles: list[tuple[int, discord.Role]] = []
        for r in guild.roles:
            if _is_level_role(r):
                th = _role_threshold(r)
                if th is not None:
                    level_roles.append((th, r))
        if not level_roles:
            return  # nothing to assign

        level_roles.sort(key=lambda t: t[0])
        # pick the highest role the member qualifies for
        target: discord.Role | None = None
        for th, role in level_roles:
            if lvl >= th:
                target = role
            else:
                break

        # remove all level roles not target; give target if missing
        to_remove = [r for _, r in level_roles if r in member.roles and r is not target]
        give = target if (target and target not in member.roles) else None

        try:
            if to_remove:
                await member.remove_roles(*to_remove, reason="Level role cleanup")
        except Exception:
            pass
        try:
            if give:
                await member.add_roles(give, reason="Level role promotion")
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(XpSystem(bot))
