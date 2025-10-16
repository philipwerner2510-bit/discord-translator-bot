import discord
from discord.ext import commands
from utils import database
import httpx

class TranslateCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        translation_channels = await database.get_translation_channels(message.guild.id)
        if message.channel.id in translation_channels:
            try:
                await message.add_reaction("🔃")
            except discord.Forbidden:
                # Bot missing reaction perms
                error_channel = await database.get_error_channel(message.guild.id)
                if error_channel:
                    ch = message.guild.get_channel(error_channel)
                    if ch:
                        await ch.send(f"❌ Missing permission to add reactions in {message.channel.mention}")
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot or str(reaction.emoji) != "🔃":
            return

        message = reaction.message
        if not message.guild:
            return

        translation_channels = await database.get_translation_channels(message.guild.id)
        if message.channel.id not in translation_channels:
            return

        await reaction.remove(user)
        try:
            await user.send("🌐 Reply with the language code (e.g., `en`, `fr`, `de`):")
            def check(m):
                return m.author == user and isinstance(m.channel, discord.DMChannel)

            dm = await self.bot.wait_for("message", check=check, timeout=60)
            lang = dm.content.strip().lower()

            async with httpx.AsyncClient() as client:
                resp = await client.post("https://libretranslate.de/translate", json={
                    "q": message.content,
                    "source": "auto",
                    "target": lang
                })
                data = resp.json()
                translated_text = data.get("translatedText", "❌ Translation failed")

            embed = discord.Embed(
                description=translated_text,
                color=0xDE002A
            )
            embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
            embed.set_footer(text=f"Translated from auto-detected language → {lang}")
            await user.send(content=translated_text, embed=embed)

        except Exception as e:
            await user.send(f"❌ Translation error: {e}")

async def setup(bot):
    await bot.add_cog(TranslateCog(bot))
