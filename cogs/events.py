# cogs/events.py  (UPDATED minimal delegator; safe to keep or remove)
import discord
from discord.ext import commands

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Keep classic event to support any existing behavior; Translate cog handles raw itself.
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