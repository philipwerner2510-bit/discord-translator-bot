import discord
from discord.ext import commands
from utils import database as db
from cogs.translate import TranslateCog

class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        channels = await db.get_reaction_channels(message.guild.id)
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
        msg = reaction.message
        await reaction.remove(user)
        # Determine language
        user_lang = await db.get_user_lang(user.id)
        if not user_lang:
            user_lang = await db.get_guild_default_lang(msg.guild.id) or "en"

        translator: TranslateCog = self.bot.get_cog("TranslateCog")
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
