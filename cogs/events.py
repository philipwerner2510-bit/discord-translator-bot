import discord
from discord.ext import commands
from utils import database as db
from cogs.translate import Translate

class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -----------------------
    # Add reaction to messages in selected channels
    # -----------------------
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        guild_id = message.guild.id
        channel_ids = await db.get_translation_channels(guild_id)
        bot_emote = await db.get_bot_emote(guild_id) or "🔃"  # fetch custom emote if set

        if channel_ids and message.channel.id in channel_ids:
            try:
                await message.add_reaction(bot_emote)
            except discord.Forbidden:
                print(f"Missing permission to react with {bot_emote} in {message.channel.name}")

    # -----------------------
    # Reaction-to-translate logic (delegates to Translate cog)
    # -----------------------
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        guild_id = reaction.message.guild.id if reaction.message.guild else None
        if not guild_id:
            return

        channel_ids = await db.get_translation_channels(guild_id)
        bot_emote = await db.get_bot_emote(guild_id) or "🔃"

        # Only react if it's in a selected channel and emoji matches the set emote
        if channel_ids and reaction.message.channel.id in channel_ids and str(reaction.emoji) == bot_emote:
            translate_cog: Translate = self.bot.get_cog("Translate")
            if translate_cog:
                await translate_cog.on_reaction_add(reaction, user)

async def setup(bot):
    await bot.add_cog(EventCog(bot))
