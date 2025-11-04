import os
import discord
from discord.ext import commands
from discord import app_commands
from utils.config import load_config, CONFIG, SUPPORTED_LANGS
from utils import database

OWNER_ID = int(os.getenv("OWNER_ID", "762267166031609858"))

def owner_only(user_id): return user_id == OWNER_ID

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
        embed.add_field(name="Timeout", value=CONFIG.reaction_timeout, inline=True)
        embed.add_field(name="Default Rate", value=CONFIG.default_rate_limit, inline=True)
        embed.add_field(name="Server Default Lang", value=srv_lang or "None", inline=False)
        embed.add_field(name="Emote", value=emote, inline=True)
        embed.add_field(name="Translation Channels", value=", ".join(f"<#{c}>" for c in chans) or "None", inline=False)
        embed.add_field(name="Error Channel", value=(f"<#{err}>" if err else "None"), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="stats", description="Bot stats.")
    @app_commands.default_permissions(manage_guild=True)
    async def stats_cmd(self, interaction: discord.Interaction):
        uptime = datetime.utcnow() - self.bot.start_time
        embed = discord.Embed(title="📈 Bot Stats", color=0xDE002A)
        embed.add_field(name="Servers", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="Uptime", value=str(uptime).split(".")[0], inline=True)
        embed.add_field(name="Translations Today", value=self.bot.total_translations, inline=True)
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

        await database.export_db(out)
        await interaction.response.send_message(f"✅ DB exported to `{out}`", ephemeral=True)

async def setup(bot):
    await bot.add_cog(OpsCommands(bot))