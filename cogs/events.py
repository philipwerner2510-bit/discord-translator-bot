import discord
from discord.ext import commands
from utils import database

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Keep track of reactions being processed to prevent duplicates
        self.processing_reactions = set()

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        # Skip bots
        if user.bot:
            return

        message_id = reaction.message.id
        user_id = user.id
        key = (message_id, user_id)

        # Ignore if already processing this message-user combination
        if key in self.processing_reactions:
            return

        self.processing_reactions.add(key)
        try:
            # Let translate.py handle the logic
            cog = self.bot.get_cog("Translate")
            if cog:
                await cog.on_reaction_add(reaction, user)
        finally:
            # Remove from processing set after completion
            self.processing_reactions.discard(key)

async def setup(bot):
    await bot.add_cog(Events(bot))
