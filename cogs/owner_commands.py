# cogs/owner_commands.py
import discord, io, asyncio
from discord.ext import commands
from discord import app_commands
from utils.brand import COLOR
from utils import database

OWNER_ID = 762267166031609858

def owner_only():
    async def predicate(interaction: discord.Interaction):
        return interaction.user.id == OWNER_ID
    return app_commands.check(predicate)

class OwnerCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="reload", description="(Owner) Reload all cogs.")
    @owner_only()
    async def reload(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        ok, fail = [], []
        for ext in list(self.bot.extensions.keys()):
            try:
                await self.bot.reload_extension(ext); ok.append(ext)
            except Exception as e:
                fail.append((ext, str(e)))
        msg = "Reloaded:\n" + "\n".join(f"• {x}" for x in ok)
        if fail:
            msg += "\n\nFailed:\n" + "\n".join(f"• {a} — {b}" for a,b in fail)
        await interaction.followup.send(msg, ephemeral=True)

    @app_commands.command(name="backup", description="(Owner) DM the SQLite DB backup.")
    @owner_only()
    async def backup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        path = database.DB_PATH
        try:
            with open(path, "rb") as f:
                data = io.BytesIO(f.read()); data.seek(0)
            file = discord.File(data, filename="bot_data.db")
            await interaction.user.send(file=file)
            await interaction.followup.send("Backup sent via DM.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Backup failed: {e}", ephemeral=True)

    @app_commands.command(name="selftest", description="(Owner) Run a quick health check.")
    @owner_only()
    async def selftest(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        issues = []
        # DB
        try:
            await database.init_db()
        except Exception as e:
            issues.append(f"DB: {type(e).__name__}")
        # OpenAI key present?
        import os
        if not os.getenv("OPENAI_API_KEY"):
            issues.append("OpenAI key missing")
        # Basic pass
        color = 0x2ecc71 if not issues else 0xe74c3c
        embed = discord.Embed(title="Self Test", description="OK" if not issues else "\n".join(issues), color=color)
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(OwnerCommands(bot))
