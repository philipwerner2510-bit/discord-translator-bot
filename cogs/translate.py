import discord
from discord.ext import commands
from discord import app_commands
from utils import database
from googletrans import Translator
import aiohttp

LIBRE_URL = "https://libretranslate.de/translate"

class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.google_translator = Translator()

    # -----------------------
    # Slash command: /translate
    # -----------------------
    @app_commands.command(name="translate", description="Translate a specific text manually.")
    async def translate(self, interaction: discord.Interaction, text: str, target_lang: str):
        await interaction.response.defer(ephemeral=True)
        try:
            translated_text, detected = await self._translate_with_fallback(text, target_lang)
            
            embed = discord.Embed(
                title="🌐 Translation",
                description=translated_text,
                color=0xde002a
            )
            embed.set_footer(text=f"Detected language: {detected} | Translated to: {target_lang}")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    # -----------------------
    # React-to-translate logic
    # -----------------------
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        message = reaction.message
        guild_id = message.guild.id if message.guild else None
        channel_ids = await database.get_translation_channels(guild_id)

        if channel_ids and message.channel.id in channel_ids:
            bot_emote = await database.get_bot_emote(guild_id) or "🔃"
            if str(reaction.emoji) != bot_emote:
                return  # Only translate if the reaction matches bot emote

            try:
                # Determine user target language
                user_lang = await database.get_user_lang(user.id)
                target_lang = user_lang or await database.get_server_lang(guild_id) or "en"

                translated_text, detected = await self._translate_with_fallback(message.content, target_lang)

                # DM embed
                embed = discord.Embed(color=0xde002a)
                embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
                embed.set_footer(text=f"Translated from: {message.content[:50]}... | Language: {target_lang}")
                await user.send(embed=embed)
                await user.send(translated_text)

                # Remove user's reaction
                await reaction.remove(user)
            except Exception as e:
                # Log error in selected error channel
                error_channel_id = await database.get_error_channel(guild_id)
                if error_channel_id:
                    ch = message.guild.get_channel(error_channel_id)
                    if ch:
                        error_embed = discord.Embed(title="❌ Translation Error", color=0xde002a)
                        error_embed.add_field(name="User", value=user.mention, inline=False)
                        error_embed.add_field(name="Original Text", value=message.content or "None", inline=False)
                        error_embed.add_field(name="Target Language", value=target_lang, inline=False)
                        error_embed.add_field(name="Error", value=str(e), inline=False)
                        await ch.send(embed=error_embed)
                else:
                    print(f"❌ Error: {e}")

    # -----------------------
    # Helper: Try LibreTranslate first, then Google
    # -----------------------
    async def _translate_with_fallback(self, text: str, target_lang: str):
        # Try LibreTranslate
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(LIBRE_URL, json={"q": text, "source": "auto", "target": target_lang}) as resp:
                    if resp.status != 200:
                        raise Exception(f"Translation API returned status {resp.status}")
                    data = await resp.json()
                    return data["translatedText"], data.get("detectedLanguage", "unknown")
        except Exception:
            # Fallback to Google Translate
            try:
                result = self.google_translator.translate(text, dest=target_lang)
                return result.text, result.src
            except Exception as e:
                raise Exception(f"All translation engines failed: {e}")

async def setup(bot):
    await bot.add_cog(Translate(bot))
