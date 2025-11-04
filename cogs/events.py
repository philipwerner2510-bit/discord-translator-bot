# cogs/events.py
import discord
from discord.ext import commands

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Minimal delegator (Translate cog handles raw reaction itself)
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        cog = self.bot.get_cog("Translate")
        if cog and hasattr(cog, "on_reaction_add"):
            try:
                await cog.on_reaction_add(reaction, user)
            except Exception:
                pass

async def setup(bot):
    await bot.add_cog(Events(bot))