# cogs/xp_system.py
# Zephyra XP System: messages, voice, translations (hook), levels, prestige, leaderboard

import asyncio
import math
import random
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks
from discord import app_commands

from utils import database
from utils.brand import COLOR, footer_text

LEVEL_ANNOUNCE_COOLDOWN = 3  # seconds anti-spam per user

# Mee6-like XP curve
def xp_needed_for_level(level: int) -> int:
    # sum_{i=0..L-1} (5i^2 + 50i + 100)
    total = 0
    for i in range(level):
        total += 5 * i * i + 50 * i + 100
    return total

def level_from_xp(xp: int) -> int:
    # binary search level
    lo, hi = 0, 1000
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if xp_needed_for_level(mid) <= xp:
            lo = mid
        else:
            hi = mid - 1
    return lo

class XPCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # track voice join timestamps: {(guild_id, user_id): ts_sec}
        self._voice_join: dict[tuple[int, int], float] = {}
        # per-user cooldown for announcing
        self._announce_gate: dict[tuple[int, int], float] = {}

    # ==========================
    # MESSAGE XP
    # ==========================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if len(message.content.strip()) < 3:
            return  # ignore tiny messages / emote spam

        gid = message.guild.id
        uid = message.author.id
        cfg = await database.get_xp_config(gid)

        gain = random.randint(cfg["msg_xp_min"], cfg["msg_xp_max"])
        await database.add_xp(gid, uid, delta_xp=gain, delta_messages=1)

        # Level-up detect & announce
        await self._maybe_announce_levelup(message.channel, message.author, gid)

    # ==========================
    # VOICE XP
    # ==========================
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot or not member.guild:
            return
        gid, uid = member.guild.id, member.id
        key = (gid, uid)

        # joined voice
        if not before.channel and after.channel:
            self._voice_join[key] = discord.utils.utcnow().timestamp()
            return

        # left voice
        if before.channel and not after.channel:
            start = self._voice_join.pop(key, None)
            if start:
                minutes = max(0, int((discord.utils.utcnow().timestamp() - start) / 60))
                if minutes > 0:
                    cfg = await database.get_xp_config(gid)
                    gain = minutes * cfg["voice_xp_per_min"]
                    await database.add_xp(gid, uid, delta_xp=gain, delta_voice_seconds=minutes * 60)
                    # announce in last text channel used? We'll DM silently (less noisy)
                    try:
                        await self._maybe_announce_levelup(member.dm_channel or await member.create_dm(), member, gid)
                    except Exception:
                        pass

    # ==========================
    # TRANSLATION XP (public hook)
    # ==========================
    async def award_translation_xp(self, guild_id: int, user_id: int):
        cfg = await database.get_xp_config(guild_id)
        await database.add_xp(guild_id, user_id, delta_xp=cfg["translate_xp"], delta_translations=1)

    # ==========================
    # Level-up announce gate + embed
    # ==========================
    async def _maybe_announce_levelup(self, channel: discord.abc.Messageable, user: discord.abc.User, gid: int):
        xp, msgs, trans, vsec = await database.get_xp(gid, user.id)
        new_level = level_from_xp(xp)
        # store last announced level in-memory gate (per process). Good enough.
        key = (gid, user.id)
        now = discord.utils.utcnow().timestamp()
        if self._announce_gate.get(key, 0) + LEVEL_ANNOUNCE_COOLDOWN > now:
            return
        self._announce_gate[key] = now

        # We can’t easily know "previous level" here without extra state.
        # Instead, announce on reaching exact threshold (rare double-counts avoided by cooldown).
        needed = xp_needed_for_level(new_level)
        if xp == needed and new_level > 0:
            cfg = await database.get_xp_config(gid)
            if not cfg["announce_levelups"]:
                return
            e = discord.Embed(
                title=f"Level Up!",
                description=f"{user.mention} reached **Level {new_level}** 🎉",
                color=COLOR,
            )
            e.set_footer(text=footer_text())
            try:
                await channel.send(embed=e)
            except Exception:
                pass

    # ==========================
    # COMMANDS: /profile /leaderboard
    # ==========================
    xp = app_commands.Group(name="xp", description="XP profile and server leaderboard")

    @xp.command(name="profile", description="Show your Zephyra XP profile")
    async def xp_profile(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        await interaction.response.defer(ephemeral=False)
        user = member or interaction.user
        gid = interaction.guild.id
        xp, msgs, trans, vsec = await database.get_xp(gid, user.id)
        level = level_from_xp(xp)
        nxt = xp_needed_for_level(level + 1)
        now_needed = max(0, nxt - xp)
        bar = self._progress_bar(xp_needed_for_level(level), nxt, xp)

        e = discord.Embed(
            title=f"{user.display_name} — Profile",
            color=COLOR,
        )
        e.add_field(name="Level", value=f"**{level}**", inline=True)
        e.add_field(name="XP", value=f"{xp:,} (next in **{now_needed:,}**)", inline=True)
        e.add_field(name="\u200b", value="\u200b", inline=True)
        e.add_field(name="Messages", value=f"{msgs:,}", inline=True)
        e.add_field(name="Translations", value=f"{trans:,}", inline=True)
        e.add_field(name="Voice", value=f"{int(vsec/60):,} min", inline=True)
        e.add_field(name="Progress", value=bar, inline=False)
        e.set_thumbnail(url=user.display_avatar.url)
        e.set_footer(text=footer_text())
        await interaction.followup.send(embed=e)

    @xp.command(name="leaderboard", description="Show the server XP leaderboard")
    async def xp_leaderboard(self, interaction: discord.Interaction, page: Optional[int] = 1):
        await interaction.response.defer(ephemeral=False)
        gid = interaction.guild.id
        per_page = 10
        offset = max(0, (page - 1) * per_page)
        rows = await database.get_xp_leaderboard(gid, per_page, offset)

        if not rows:
            await interaction.followup.send("No XP yet. Start chatting and translating!")
            return

        lines = []
        rank = offset + 1
        for uid, xp, msgs, trans, vsec in rows:
            member = interaction.guild.get_member(uid)
            name = member.display_name if member else f"User {uid}"
            lvl = level_from_xp(xp)
            lines.append(f"**{rank}. {name}** — Lvl {lvl} • {xp:,} XP • {msgs:,} msgs • {trans:,} tr • {int(vsec/60):,} min")
            rank += 1

        e = discord.Embed(
            title=f"XP Leaderboard — Page {page}",
            description="\n".join(lines),
            color=COLOR,
        )
        e.set_footer(text=footer_text())
        await interaction.followup.send(embed=e)

    def _progress_bar(self, start: int, end: int, value: int, width: int = 20) -> str:
        if end <= start:
            return "■" * width
        frac = (value - start) / (end - start)
        filled = max(0, min(width, int(round(frac * width))))
        return "■" * filled + "□" * (width - filled)

    # ==========================
    # ADMIN CONFIG: /xpconfig ...
    # ==========================
    xpconfig = app_commands.Group(name="xpconfig", description="Configure XP settings (admins only)")

    def _admin_check(self, it: discord.Interaction) -> bool:
        return it.user.guild_permissions.manage_guild

    @xpconfig.command(name="show", description="Show current XP configuration")
    async def cfg_show(self, interaction: discord.Interaction):
        if not self._admin_check(interaction):
            await interaction.response.send_message("You need **Manage Server**.", ephemeral=True)
            return
        cfg = await database.get_xp_config(interaction.guild.id)
        e = discord.Embed(
            title="XP Configuration",
            color=COLOR,
            description=(
                f"Message XP: **{cfg['msg_xp_min']}–{cfg['msg_xp_max']}**\n"
                f"Translate XP: **{cfg['translate_xp']}**\n"
                f"Voice XP per min: **{cfg['voice_xp_per_min']}**\n"
                f"Announce level-ups: **{'On' if cfg['announce_levelups'] else 'Off'}**\n"
                f"Prestige threshold: **{cfg['prestige_threshold']:,} XP**"
            )
        )
        e.set_footer(text=footer_text())
        await interaction.response.send_message(embed=e, ephemeral=True)

    @xpconfig.command(name="message", description="Set message XP range")
    @app_commands.describe(min_xp="Minimum XP per message", max_xp="Maximum XP per message")
    async def cfg_message(self, interaction: discord.Interaction, min_xp: int, max_xp: int):
        if not self._admin_check(interaction):
            await interaction.response.send_message("You need **Manage Server**.", ephemeral=True)
            return
        if min_xp < 0 or max_xp < 0 or max_xp < min_xp:
            await interaction.response.send_message("Invalid range.", ephemeral=True)
            return
        await database.set_xp_config(interaction.guild.id, msg_xp_min=min_xp, msg_xp_max=max_xp)
        await interaction.response.send_message(f"Message XP updated: **{min_xp}–{max_xp}**", ephemeral=True)

    @xpconfig.command(name="translate", description="Set XP per translation")
    async def cfg_translate(self, interaction: discord.Interaction, xp_per_translation: int):
        if not self._admin_check(interaction):
            await interaction.response.send_message("You need **Manage Server**.", ephemeral=True)
            return
        if xp_per_translation < 0:
            await interaction.response.send_message("Invalid value.", ephemeral=True)
            return
        await database.set_xp_config(interaction.guild.id, translate_xp=xp_per_translation)
        await interaction.response.send_message(f"Translate XP set to **{xp_per_translation}**", ephemeral=True)

    @xpconfig.command(name="voice", description="Set XP gained per minute in voice")
    async def cfg_voice(self, interaction: discord.Interaction, xp_per_minute: int):
        if not self._admin_check(interaction):
            await interaction.response.send_message("You need **Manage Server**.", ephemeral=True)
            return
        if xp_per_minute < 0:
            await interaction.response.send_message("Invalid value.", ephemeral=True)
            return
        await database.set_xp_config(interaction.guild.id, voice_xp_per_min=xp_per_minute)
        await interaction.response.send_message(f"Voice XP per minute set to **{xp_per_minute}**", ephemeral=True)

    @xpconfig.command(name="announce", description="Toggle level-up announcements")
    async def cfg_announce(self, interaction: discord.Interaction, enabled: bool):
        if not self._admin_check(interaction):
            await interaction.response.send_message("You need **Manage Server**.", ephemeral=True)
            return
        await database.set_xp_config(interaction.guild.id, announce_levelups=enabled)
        await interaction.response.send_message(f"Level-up announcements **{'enabled' if enabled else 'disabled'}**.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(XPCog(bot))
