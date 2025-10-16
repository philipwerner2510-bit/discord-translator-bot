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
        bot_emote = await db.get_bot_emote(guild_id)  # fetch custom emote if set

        if channel_ids and message.channel.id in channel_ids:
            if bot_emote:
                try:
                    await message.add_reaction(bot_emote)
                except discord.Forbidden:
                    print(f"Missing permission to react with {bot_emote} in {message.channel.name}")
            else:
                # default emoji 🔃
                try:
                    await message.add_reaction("🔃")
                except discord.Forbidden:
                    print(f"Missing permission to react in {message.channel.name}")

    # -----------------------
    # Reaction-to-translate logic (delegates to Translate cog)
    # -----------------------
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        if str(reaction.emoji) not in ["🔃"]:
            # you can expand this if you allow custom emotes for translation
            return

        translate_cog: Translate = self.bot.get_cog("Translate")
        if translate_cog:
            await translate_cog.on_reaction_add(reaction, user)

async def setup(bot):
    await bot.add_cog(EventCog(bot))
