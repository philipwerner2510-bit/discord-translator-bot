import discord
from discord.ext import commands
from utils import database

class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_listener(self.on_reaction_add)
        self.bot.add_listener(self.on_message)

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
        if user.bot or str(reaction.emoji) != "🔃":
            return
        msg = reaction.message
        await reaction.remove(user)

        # Determine language
        user_lang = await database.get_user_lang(user.id)
        target_lang = user_lang or await database.get_server_lang(msg.guild.id) or "en"

        # Translation via Libre
        async with aiohttp.ClientSession() as session:
            async with session.post("https://libretranslate.de/translate", json={"q": msg.content, "source": "auto", "target": target_lang}) as resp:
                data = await resp.json()
                translated = data.get("translatedText", msg.content)
                detected = data.get("detectedLanguage", "unknown")

        # Embed DM
        embed = discord.Embed(description=translated, color=0xde002a)
        embed.set_author(name=msg.author.display_name, icon_url=msg.author.display_avatar.url)
        embed.set_footer(text=f"Detected language: {detected} | Translated to: {target_lang}")
        try:
            await user.send(embed=embed)
        except discord.Forbidden:
            print(f"Cannot DM user {user}.")

async def setup(bot):
    await bot.add_cog(EventCog(bot))
