import discord
from discord.ext import commands
from utils import database as db
from cogs.translate import Translate

class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        channels = await db.get_translation_channels(message.guild.id)
        if message.channel.id in channels:
            emote = await db.get_custom_emote(message.guild.id)
            try:
                await message.add_reaction(emote)
            except discord.Forbidden:
                print(f"Missing permission to add reactions in {message.channel.name}")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        emote = await db.get_custom_emote(reaction.message.guild.id)
        if str(reaction.emoji) != emote:
            return
        msg = reaction.message

        await reaction.remove(user)

        user_lang = await db.get_user_lang(user.id)
        if not user_lang:
            user_lang = await db.get_server_lang(msg.guild.id) or "en"

        translator: Translate = self.bot.get_cog("Translate")
        translated = await translator.translate_text(msg.content, user_lang)

        embed = discord.Embed(
            description=translated,
            color=0xDE002A
        )
        embed.set_author(name=msg.author.display_name, icon_url=msg.author.display_avatar.url)
        embed.set_footer(text=f"Translated from {msg.content[:50]}... | Language: {user_lang}")

        try:
            await user.send(content="🌐 Translation:", embed=embed)
        except discord.Forbidden:
            print(f"Cannot DM user {user}.")

async def setup(bot):
    await bot.add_cog(EventCog(bot))
