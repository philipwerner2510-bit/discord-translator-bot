import discord
from discord.ext import commands
from utils import database

from cogs.translate import Translate  # matches the class name now

class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        channels = await database.get_translation_channels(message.guild.id)
        if message.channel.id in channels:
            try:
                # Fetch the current emote from DB or default 🔃
                emote = await database.get_reaction_emote(message.guild.id) or "🔃"
                await message.add_reaction(emote)
            except discord.Forbidden:
                print(f"Missing permission to add reactions in {message.channel.name}")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        if str(reaction.emoji) not in ["🔃"]:  # add other custom emotes if needed
            return
        msg = reaction.message
        await reaction.remove(user)

        # Determine language
        user_lang = await database.get_user_lang(user.id)
        if not user_lang:
            user_lang = await database.get_server_lang(msg.guild.id) or "en"

        translator: Translate = self.bot.get_cog("Translate")
        translated = await translator.translate_text(msg.content, user_lang)

        # DM with embed
        embed = discord.Embed(
            description=translated,
            color=0xDE002A
        )
        embed.set_author(name=msg.author.display_name, icon_url=msg.author.display_avatar.url)
        embed.set_footer(text=f"Translated from {msg.content[:50]}... | Language: {user_lang}")
        try:
            await user.send(content=f"🌐 Translation:", embed=embed)
        except discord.Forbidden:
            print(f"Cannot DM user {user}.")

async def setup(bot):
    await bot.add_cog(EventCog(bot))
