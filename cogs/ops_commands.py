# cogs/ops_commands.py
import os
import discord
from discord.ext import commands
from discord import app_commands
from utils.brand import COLOR, footer_text as _footer_text

def FOOT(): return _footer_text() if callable(_footer_text) else _footer_text
OWNER_IDS = {int(x) for x in os.getenv("OWNER_IDS","1425590836800000170").split(",") if x.strip().isdigit()}

def check_owner():
    def predicate(interaction: discord.Interaction) -> bool:
        return interaction.user.id in OWNER_IDS
    return app_commands.check(predicate)

class Ops(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="ping", description="Show bot latency.")
    async def ping(self, interaction: discord.Interaction):
        e = discord.Embed(title="Pong!", description=f"Latency: {round(self.bot.latency*1000)} ms", color=COLOR)
        e.set_footer(text=FOOT())
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="reload", description="(Owner) Reload all cogs.")
    @check_owner()
    async def reload(self, interaction: discord.Interaction):
        failed = []
        for ext in list(self.bot.extensions.keys()):
            try:
                await self.bot.reload_extension(ext)
            except Exception as ex:
                failed.append(f"{ext}: {ex}")
        msg = "Reloaded all cogs." if not failed else "Reload completed with errors:\n" + "\n".join(failed)
        e = discord.Embed(title="Reload", description=msg, color=COLOR).set_footer(text=FOOT())
        await interaction.response.send_message(embed=e, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Ops(bot))
