# cogs/ops_commands.py
import os
from datetime import datetime
import discord
from discord.ext import commands
from discord import app_commands

from utils.config import load_config, CONFIG, SUPPORTED_LANGS
from utils import database
from utils.logging_utils import LOG_FILE as LOG_PATH  # alias to the log path

OWNER_ID = int(os.getenv("OWNER_ID", "762267166031609858"))


def owner_only(user_id: int) -> bool:
    return user_id == OWNER_ID


def humanize_delta(dt: datetime) -> str:
    delta = datetime.utcnow() - dt
    secs = int(delta.total_seconds())
    days, secs = divmod(secs, 86400)
    hours, secs = divmod(secs, 3600)
    minutes, secs = divmod(secs, 60)
    parts = []
    if days: parts.append(f"{days}d")
    if hours: parts.append(f"{hours}h")
    if minutes: parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


async def tail_file(path: str, n: int = 10) -> list[str]:
    """Return last n lines of a text file safely."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        return [line.rstrip("\n") for line in lines[-n:]]
    except FileNotFoundError:
        return ["<no log file yet>"]
    except Exception as e:
        return [f"<error reading logs: {e}>"]


def build_recommended_permissions_value() -> int:
    """
    Recommended permission set:
    - View Channel, Send Messages, Read Message History, Add Reactions, Embed Links, Manage Messages
    """
    p = discord.Permissions(
        view_channel=True,
        send_messages=True,
        read_message_history=True,
        add_reactions=True,
        embed_links=True,
        manage_messages=True,
    )
    return p.value


def make_invite_links(bot: commands.Bot) -> tuple[str, str]:
    """Returns (recommended_link, minimal_link)."""
    client_id = bot.user.id  # type: ignore
    scopes = "bot%20applications.commands"
    perms_val = build_recommended_permissions_value()
    recommended = (
        f"https://discord.com/api/oauth2/authorize?client_id={client_id}"
        f"&scope={scopes}&permissions={perms_val}"
    )
    minimal = (
        f"https://discord.com/api/oauth2/authorize?client_id={client_id}"
        f"&scope={scopes}&permissions=0"
    )
    return recommended, minimal


def get_recent_guilds(bot: commands.Bot, n: int = 5) -> list[tuple[discord.Guild, datetime | None]]:
    """Sort guilds by when the bot joined (desc), None last."""
    pairs: list[tuple[discord.Guild, datetime | None]] = []
    for g in bot.guilds:
        joined = None
        try:
            joined = getattr(g.me, "joined_at", None)
        except Exception:
            pass
        pairs.append((g, joined))
    pairs.sort(key=lambda x: (x[1] is None, x[1] if x[1] else datetime.min), reverse=True)
    return pairs[:n]


class RestartView(discord.ui.View):
    def __init__(self, invoker_id: int):
        super().__init__(timeout=60)
        self.invoker_id = invoker_id

    @discord.ui.button(label="Restart bot", style=discord.ButtonStyle.danger)
    async def restart_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.invoker_id:
            return await interaction.response.defer()
        await interaction.response.edit_message(content="♻️ Restarting the bot… see you in a few seconds.", view=None)
        os._exit(0)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.invoker_id:
            return await interaction.response.defer()
        await interaction.response.edit_message(content="✅ Cancelled.", view=None)


class InviteLinksView(discord.ui.View):
    """Shown in the owner's DM — has URL buttons to invite quickly."""
    def __init__(self, recommended_url: str, minimal_url: str):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Invite (Recommended)", style=discord.ButtonStyle.link, url=recommended_url))
        self.add_item(discord.ui.Button(label="Invite (Minimal)", style=discord.ButtonStyle.link, url=minimal_url))


class OpsCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="config", description="Bot config & wiring.")
    @app_commands.default_permissions(manage_guild=True)
    async def config_cmd(self, interaction: discord.Interaction):
        gid = interaction.guild.id
        err = await database.get_error_channel(gid)
        chans = await database.get_translation_channels(gid)
        srv_lang = await database.get_server_lang(gid)
        emote = await database.get_bot_emote(gid) or "🔃"

        embed = discord.Embed(title="⚙️ Bot Config", color=0xDE002A)
        embed.add_field(name="DB Path", value=os.getenv("BOT_DB_PATH", "/mnt/data/bot_data.db"), inline=False)
        embed.add_field(name="Supported Languages", value=str(len(SUPPORTED_LANGS)), inline=True)
        embed.add_field(name="Reaction Timeout", value=str(CONFIG.reaction_timeout), inline=True)
        embed.add_field(name="Default Rate", value=str(CONFIG.default_rate_limit), inline=True)
        embed.add_field(name="Server Default Lang", value=srv_lang or "None", inline=False)
        embed.add_field(name="Emote", value=emote, inline=True)
        embed.add_field(name="Translation Channels", value=", ".join(f"<#{c}>" for c in chans) or "None", inline=False)
        embed.add_field(name="Error Channel", value=(f"<#{err}>" if err else "None"), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="stats", description="Bot stats.")
    @app_commands.default_permissions(manage_guild=True)
    async def stats_cmd(self, interaction: discord.Interaction):
        uptime = humanize_delta(self.bot.start_time)
        embed = discord.Embed(title="📈 Bot Stats", color=0xDE002A)
        embed.add_field(name="Servers", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="Uptime", value=uptime, inline=True)
        embed.add_field(name="Translations Today", value=self.bot.total_translations, inline=True)
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="reloadconfig", description="Reload config.json (owner)")
    async def reloadconfig_cmd(self, interaction: discord.Interaction):
        if not owner_only(interaction.user.id):
            return await interaction.response.send_message("❌ Owner only.", ephemeral=True)
        load_config()
        await interaction.response.send_message("✅ Config reloaded.", ephemeral=True)

    @app_commands.command(name="exportdb", description="Export DB backup (owner)")
    async def exportdb_cmd(self, interaction: discord.Interaction):
        if not owner_only(interaction.user.id):
            return await interaction.response.send_message("❌ Owner only.", ephemeral=True)

        ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        base = os.getenv("BOT_DB_PATH", "/mnt/data/bot_data.db")
        out = base.replace("bot_data.db", f"backup-{ts}.db")

        path = await database.export_db(out)
        await interaction.response.send_message(f"✅ DB exported to `{path}`", ephemeral=True)

    # ====== Owner control panel ======
    @app_commands.command(name="summonpolarix", description="Owner diagnostics + controls.")
    async def summonpolarix_cmd(self, interaction: discord.Interaction):
        if not owner_only(interaction.user.id):
            return await interaction.response.send_message("❌ Owner only.", ephemeral=True)

        uptime = humanize_delta(self.bot.start_time)
        recommended, minimal = make_invite_links(self.bot)

        # Build DM embed (with recent guilds + invite links)
        diag = discord.Embed(title="🧰 Demon Bot — Owner Diagnostics", color=0xDE002A)
        diag.add_field(name="Servers", value=str(len(self.bot.guilds)), inline=True)
        diag.add_field(name="Uptime", value=uptime, inline=True)
        diag.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        diag.add_field(name="Process PID", value=str(os.getpid()), inline=True)

        recents = get_recent_guilds(self.bot, 5)
        if recents:
            lines = []
            for g, ts in recents:
                when = ts.strftime("%Y-%m-%d") if ts else "—"
                lines.append(f"• {g.name} (`{g.id}`) — {when}")
            diag.add_field(name="Recent Servers", value="\n".join(lines), inline=False)

        diag.add_field(
            name="Invite Links",
            value="Use the buttons below to open the links.",
            inline=False
        )
        diag.set_footer(text="Created by Polarix1954")

        dm_status = ""
        try:
            await interaction.user.send(embed=diag, view=InviteLinksView(recommended, minimal))
            dm_status = "📩 Sent you a diagnostic DM (with invite buttons)."
        except discord.Forbidden:
            dm_status = "⚠️ Could not DM you (privacy settings)."

        # Ephemeral console with logs + restart
        lines = await tail_file(LOG_PATH, n=10)
        formatted = "\n".join(f"• {l}"[:190] for l in lines) or "<empty>"
        embed = discord.Embed(title="👑 Owner Console", color=0xDE002A, description=dm_status)
        embed.add_field(name="Last 10 log lines", value=f"```\n{formatted}\n```", inline=False)
        view = RestartView(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(OpsCommands(bot))