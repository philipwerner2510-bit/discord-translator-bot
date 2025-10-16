import discord
from discord.ext import commands
from utils import database as db
from googletrans import Translator

class TranslateCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.translator = Translator()

    # -----------------------------
    # Reaction listener for translation
    # -----------------------------
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user.bot:
            return

        message = reaction.message
        guild_id = message.guild.id if message.guild else None
        if not guild_id:
            return  # Only in guilds

        # Get channels enabled for translation in this guild
        translation_channels = await db.get_translation_channels(guild_id)
        if message.channel.id not in translation_channels:
            return

        # Only trigger on 🔃
        if str(reaction.emoji) != "🔃":
            return

        # Remove user reaction immediately
        try:
            await message.remove_reaction(reaction.emoji, user)
        except discord.Forbidden:
            pass  # Bot may not have permissions

        # Determine target language
        user_lang = await db.get_user_lang(user.id)
        if not user_lang:
            # fallback to server default
            user_lang = await db.get_server_lang(guild_id) or "en"

        # Translate the message
        try:
            translated = await self.bot.loop.run_in_executor(
                None, lambda: self.translator.translate(message.content, dest=user_lang)
            )
        except Exception as e:
            # Log to error channel if set
            error_channel_id = await db.get_error_channel(guild_id)
            if error_channel_id:
                channel = self.bot.get_channel(error_channel_id)
                if channel:
                    await channel.send(f"[Guild {guild_id}] on_reaction_add error: {e}")
            return

        # Send DM to user
        try:
            embed = discord.Embed(
                title=f"Translation from {message.author.display_name}",
                description=translated.text,
                color=0xDE002A
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)
            embed.set_footer(text=f"Detected: {translated.src} | Translated to: {translated.dest}")

            await user.send(embed=embed)
        except discord.Forbidden:
            # User has DMs closed
            pass

    # -----------------------------
    # Optional helper function for manual translation
    # -----------------------------
    async def translate_text(self, text: str, dest: str) -> str:
        return (await self.bot.loop.run_in_executor(None, lambda: self.translator.translate(text, dest=dest))).text


async def setup(bot):
    await bot.add_cog(TranslateCog(bot))
