import discord
from discord.ext import commands
from utils import database

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
                await message.add_reaction("🔃")
            except discord.Forbidden:
                print(f"Missing permission to add reactions in {message.channel.name}")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        if str(reaction.emoji) != "🔃":
            return
        message = reaction.message
        guild_id = message.guild.id
        channels = await database.get_translation_channels(guild_id)
        if message.channel.id not in channels:
            return

        user_lang = await database.get_user_lang(user.id)
        if not user_lang:
            user_lang = await database.get_server_lang(guild_id) or "en"

        translator = self.bot.get_cog("TranslateCog")
        translated_text, detected = await translator.translate_text(message.content, user_lang)

        embed = discord.Embed(color=0xde002a)
        embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
        embed.set_footer(text=f"Translated from {message.content[:50]}... | Language: {user_lang}")
        try:
            await user.send(content="🌐 Translation:", embed=embed)
            await user.send(translated_text)
        except discord.Forbidden:
            print(f"Cannot DM user {user}.")

async def setup(bot):
    await bot.add_cog(EventCog(bot))
