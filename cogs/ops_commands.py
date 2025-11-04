# cogs/ops_commands.py
import os
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from utils.config import CONFIG, SUPPORTED_LANGS, load_config
from utils import database

# Use env var if set, otherwise default to your ID
OWNER_ID = int(os.getenv("OWNER_ID", "762267166031609858"))

def _owner_only(interaction: discord.Interaction) -> bool:
    return OWNER_ID and interaction.user.id == OWNER_ID

class OpsCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(name="config", description="Show current bot configuration & server wiring.")
    async def config_cmd(self, interaction: discord.Interaction):
        gid = interaction.guild.id
        err_ch = await database.get_error_channel(gid)
        channels = await database.get_translation_channels(gid)
        server_lang = await database.get_server_lang(gid)
        emote = await database.get_bot_emote(gid) or "🔃"

        embed = discord.Embed(title="⚙️ Bot Configuration", color=0xDE002A)
        embed.add_field(name="Config file", value=os.getenv("BOT_CONFIG_PATH", "config.json"), inline=False)
        embed.add_field(name="Supported languages", value=str(len(SUPPORTED_LANGS)), inline=True)
        embed.add_field(name="Reaction timeout (s)", value=str(CONFIG.reaction_timeout), inline=True)
        embed.add_field(name="Default rate limit", value=str(CONFIG.default_rate_limit), inline=True)
        embed.add_field(name="DB path", value=os.getenv("BOT_DB_PATH", "/mnt/data/bot_data.db"), inline=False)

        embed.add_field(name="Server default lang", value=server_lang or "Not set", inline=True)
        embed.add_field(name="Bot emote", value=emote, inline=True)
        ch_val = ", ".join(f"<#{c}>" for c in channels) if channels else "None"
        embed.add_field(name="Translation channels", value=ch_val, inline=False)
        embed.add_field(name="Error channel", value=(f"<#{err_ch}>" if err_ch else "Not set"), inline=False)

        # runtime stats
        start = getattr(self.bot, "start_time", None)
        if start:
            uptime = datetime.utcnow() - start
            embed.add_field(name="Uptime", value=str(uptime).split(".")[0], inline=True)
        embed.add_field(name="Total translations (today)", value=str(getattr(self.bot, "total_translations", 0)), inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(name="stats", description="Show live stats: uptime, servers, translations.")
    async def stats_cmd(self, interaction: discord.Interaction):
        start = getattr(self.bot, "start_time", None)
        uptime = str((datetime.utcnow() - start)).split(".")[0] if start else "—"
        embed = discord.Embed(title="📈 Bot Stats", color=0xDE002A)
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="Uptime", value=uptime, inline=True)
        embed.add_field(name="Translations (today)", value=str(getattr(self.bot, "total_translations", 0)), inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="reloadconfig", description="Owner: reload config.json without redeploy.")
    async def reloadconfig_cmd(self, interaction: discord.Interaction):
        if not _owner_only(interaction):
            return await interaction.response.send_message("❌ Owner only.", ephemeral=True)
        from utils import config as cfg_mod
        new_cfg = load_config()
        cfg_mod.CONFIG = new_cfg
        cfg_mod.SUPPORTED_LANGS = new_cfg.supported_langs
        await interaction.response.send_message("✅ Config reloaded.", ephemeral=True)

    @app_commands.command(name="exportdb", description="Owner: export a DB backup file.")
    async def exportdb_cmd(self, interaction: discord.Interaction):
        if not _owner_only(interaction):
            return await interaction.response.send_message("❌ Owner only.", ephemeral=True)

        ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        base = os.getenv("BOT_DB_PATH", "/mnt/data/bot_data.db")
        out = f"/mnt/data/backup-{ts}.db" if base.startswith("/mnt/data") else f"backup-{ts}.db"

        await interaction.response.defer(ephemeral=True)
        try:
            await database.export_db(out)
        except Exception as e:
            return await interaction.followup.send(f"❌ Export failed: {e}", ephemeral=True)

        try:
            await interaction.followup.send(content=f"✅ Exported to `{out}`", file=discord.File(out), ephemeral=True)
        except Exception:
            await interaction.followup.send(f"✅ Exported to `{out}` (couldn’t attach file; fetch from volume).", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(OpsCommands(bot))