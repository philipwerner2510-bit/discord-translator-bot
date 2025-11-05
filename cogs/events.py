import discord
from discord.ext import commands

class Events(commands.Cog):
    def __init__(self, bot): self.bot = bot
    processing = set()

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot: return
        key = (reaction.message.id, user.id)
        if key in self.processing: return
        self.processing.add(key)
        try:
            cog = self.bot.get_cog("Translate")
            if cog:
                await cog.on_reaction_add(reaction, user)
        finally:
            self.processing.discard(key)

async def setup(bot): await bot.add_cog(Events(bot))
