import os, discord
from discord.ext import commands
from discord import app_commands
from utils.brand import COLOR, footer

OWNER_ID = int(os.getenv("OWNER_ID", "762267166031609858"))

def owner_only():
    def predicate(it: discord.Interaction):
        return it.user.id == OWNER_ID
    return app_commands.check(lambda it: predicate(it))

class Owner(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="reload", description="Owner: reload a cog by name (e.g., cogs.translate).")
    @owner_only()
    async def reload(self, interaction: discord.Interaction, cog: str):
        try:
            await self.bot.reload_extension(cog)
            e = discord.Embed(description=f"✅ Reloaded `{cog}`", color=COLOR)
        except Exception as e:
            e = discord.Embed(description=f"❌ Reload failed: `{e}`", color=COLOR)
        e.set_footer(text=footer()); await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="stats", description="Owner: show bot stats.")
    @owner_only()
    async def stats(self, interaction: discord.Interaction):
        guilds = len(self.bot.guilds); latency = round(self.bot.latency*1000)
        e = discord.Embed(title="Owner Stats", description=f"Guilds: **{guilds}**\nLatency: **{latency} ms**", color=COLOR)
        e.set_footer(text=footer()); await interaction.response.send_message(embed=e, ephemeral=True)

async def setup(bot): await bot.add_cog(Owner(bot))
