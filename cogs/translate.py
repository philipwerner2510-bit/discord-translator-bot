import discord
from discord.ext import commands
from googletrans import Translator
from utils import database as db

class TranslateCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.translator = Translator()

    async def translate_text(self, text, lang):
        try:
            result = self.translator.translate(text, dest=lang)
            return result.text
        except Exception:
            return "❌ Translation failed."

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        guild_id = reaction.message.guild.id
        translation_channels = await db.get_translation_channels(guild_id)
        if translation_channels and reaction.message.channel.id in translation_channels:
            if str(reaction.emoji) == "🔃":
                await reaction.remove(user)
                try:
                    await user.send("🌐 Please reply with a language code (e.g., `en`, `fr`, `de`):")

                    def check(m):
                        return m.author == user and isinstance(m.channel, discord.DMChannel)

                    reply = await self.bot.wait_for("message", check=check, timeout=60)
                    lang = reply.content.strip().lower()
                    translated = await self.translate_text(reaction.message.content, lang)
                    
                    embed = discord.Embed(
                        title="Translated Message",
                        description=translated,
                        color=0xDE002A
                    )
                    embed.set_author(name=reaction.message.author.name, icon_url=reaction.message.author.display_avatar.url)
                    embed.set_footer(text=f"Original Language: {reaction.message.content[:10]} | Translated to: {lang}")

                    await user.send(embed=embed)
                except Exception as e:
                    await user.send(f"❌ Error: {e}")

async def setup(bot):
    await bot.add_cog(TranslateCog(bot))
