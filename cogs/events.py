import discord
from discord.ext import commands
from utils import database as db
from cogs.translate import Translate

class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -----------------------
    # Auto react to messages
    # -----------------------
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        channels = await db.get_translation_channels(message.guild.id)
        if message.channel.id in channels:
            emote = await db.get_server_emote(message.guild.id)  # fetch custom emote
            try:
                if emote:
                    await message.add_reaction(emote)
                else:
                    await message.add_reaction("🔃")
            except discord.Forbidden:
                print(f"Missing permission to add reactions in {message.channel.name}")

    # -----------------------
    # React-to-translate logic
    # -----------------------
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot or not reaction.message.guild:
            return
        guild_id = reaction.message.guild.id
        channel_ids = await db.get_translation_channels(guild_id)
        emote = await db.get_server_emote(guild_id) or "🔃"

        if reaction.message.channel.id in channel_ids and str(reaction.emoji) == emote:
            try:
                user_lang = await db.get_user_lang(user.id)
                target_lang = user_lang or await db.get_server_lang(guild_id) or "en"

                translator: Translate = self.bot.get_cog("Translate")
                translated_text, detected = await translator.translate_text(reaction.message.content, target_lang)

                embed = discord.Embed(color=0xDE002A)
                embed.set_author(
                    name=reaction.message.author.display_name,
                    icon_url=reaction.message.author.display_avatar.url
                )
                embed.set_footer(text=f"Translated from {reaction.message.content[:50]}... | Language: {detected}")
                await user.send(embed=embed)
                await user.send(translated_text)
                await reaction.remove(user)
            except Exception as e:
                error_channel_id = await db.get_error_channel(guild_id)
                if error_channel_id:
                    ch = reaction.message.guild.get_channel(error_channel_id)
                    if ch:
                        await ch.send(f"❌ Error while translating: {e}")
                else:
                    print(f"[Guild {guild_id}] Error: {e}")

async def setup(bot):
    await bot.add_cog(EventCog(bot))
