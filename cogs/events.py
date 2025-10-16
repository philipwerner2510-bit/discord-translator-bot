import discord
from discord.ext import commands
from utils import database

class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -----------------------
    # Add reaction automatically
    # -----------------------
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        channels = await database.get_translation_channels(message.guild.id)
        if message.channel.id in channels:
            try:
                emotes = await database.get_reaction_emotes(message.guild.id) or ["🔃"]
                for emote in emotes:
                    await message.add_reaction(emote)
            except discord.Forbidden:
                print(f"Missing permission to add reactions in {message.channel.name}")

async def setup(bot):
    await bot.add_cog(EventCog(bot))
