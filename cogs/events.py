import discord
from discord.ext import commands
from utils import database
from cogs.translate import Translate

class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -----------------------
    # Add reaction to messages in selected channels
    # -----------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        guild_id = message.guild.id
        channel_ids = await database.get_translation_channels(guild_id)
        bot_emote = await database.get_bot_emote(guild_id) or "🔃"

        if channel_ids and message.channel.id in channel_ids:
            try:
                await message.add_reaction(bot_emote)
            except discord.Forbidden:
                print(f"Missing permission to react with {bot_emote} in {message.channel.name}")

    # -----------------------
    # Handle reaction-to-translate logic
    # -----------------------
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user.bot or not reaction.message.guild:
            return

        guild_id = reaction.message.guild.id
        channel_ids = await database.get_translation_channels(guild_id)
        bot_emote = await database.get_bot_emote(guild_id) or "🔃"

        # Only proceed if reaction emoji matches the bot emote
        if channel_ids and reaction.message.channel.id in channel_ids and str(reaction.emoji) == bot_emote:
            translate_cog: Translate = self.bot.get_cog("Translate")
            if translate_cog:
                await translate_cog.on_reaction_add(reaction, user)

async def setup(bot):
    await bot.add_cog(EventCog(bot))
