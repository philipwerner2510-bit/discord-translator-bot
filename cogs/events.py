import discord
from discord.ext import commands
from utils import database as db
from cogs.translate import Translate

class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        channels = await db.get_translation_channels(message.guild.id)
        if message.channel.id in channels:
            try:
                emote = await db.get_guild_emote(message.guild.id)
                await message.add_reaction(emote)
            except discord.Forbidden:
                print(f"Missing permission to add reactions in {message.channel.name}")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        message = reaction.message
        guild_id = message.guild.id if message.guild else None
        if not guild_id:
            return

        channels = await db.get_translation_channels(guild_id)
        if message.channel.id not in channels:
            return

        if str(reaction.emoji) != await db.get_guild_emote(guild_id):
            return

        await reaction.remove(user)

        # Determine language
        user_lang = await db.get_user_lang(user.id)
        if not user_lang:
            user_lang = await db.get_server_lang(guild_id) or "en"

        translator: Translate = self.bot.get_cog("Translate")
        translated_text, detected = await translator.translate_text(message.content, user_lang)

        # DM with embed
        embed = discord.Embed(
            description=translated_text,
            color=0xDE002A
        )
        embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
        embed.set_footer(text=f"Translated from {message.content[:50]}... | Language: {user_lang}")
        try:
            await user.send(content="🌐 Translation:", embed=embed)
        except discord.Forbidden:
            print(f"Cannot DM user {user}.")

async def setup(bot):
    await bot.add_cog(EventCog(bot))
