import discord
from discord.ext import commands
from discord import app_commands
from utils import database
import aiohttp
import asyncio

LIBRE_URL = "https://libretranslate.de/translate"

# Optional: placeholders for Google / Microsoft free APIs
GOOGLE_URL = "https://translation.googleapis.com/language/translate/v2"  # requires API key
MICROSOFT_URL = "https://api.cognitive.microsofttranslator.com/translate?api-version=3.0"  # requires key

class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -----------------------
    # Slash command: /translate
    # -----------------------
    @app_commands.command(name="translate", description="Translate a specific text manually.")
    async def translate(self, interaction: discord.Interaction, text: str, target_lang: str):
        await interaction.response.defer(ephemeral=True)
        try:
            translated_text, detected = await self.translate_text_with_fallback(text, target_lang)
            embed = discord.Embed(
                title="🌐 Translation",
                color=0xde002a
            )
            embed.set_footer(text=f"Detected language: {detected} | Translated to: {target_lang}")
            await interaction.followup.send(embed=embed)
            await interaction.followup.send(translated_text)
        except Exception as e:
            await self.send_error_embed(interaction, e, user=interaction.user, original_text=text)

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
        bot_emote = await database.get_bot_emote(guild_id) or "🔃"

        if channel_ids and message.channel.id in channel_ids and str(reaction.emoji) == bot_emote:
            try:
                user_lang = await database.get_user_lang(user.id)
                target_lang = user_lang or await database.get_server_lang(guild_id) or "en"

                translated_text, detected = await self.translate_text_with_fallback(message.content, target_lang)

                embed = discord.Embed(color=0xde002a)
                embed.set_author(
                    name=message.author.display_name,
                    icon_url=message.author.display_avatar.url
                )
                embed.set_footer(text=f"Translated from {message.content[:50]}... | Language: {target_lang}")

                await user.send(embed=embed)
                await user.send(translated_text)

                # Remove reaction after successful translation
                await reaction.remove(user)

            except Exception as e:
                await self.send_error_embed_to_channel(message, user, message.content, e)

    # -----------------------
    # Translation helper with fallback
    # -----------------------
    async def translate_text_with_fallback(self, text: str, target_lang: str):
        # Try LibreTranslate first
        try:
            return await self.translate_libre(text, target_lang)
        except Exception as e1:
            print(f"LibreTranslate failed: {e1}")
            # TODO: add Google / Microsoft API integration here if you have keys
            raise Exception("Translation failed on all available free engines.")

    async def translate_libre(self, text: str, target_lang: str):
        async with aiohttp.ClientSession() as session:
            async with session.post(LIBRE_URL, json={"q": text, "source": "auto", "target": target_lang}) as resp:
                if resp.status != 200:
                    raise Exception(f"Translation API returned status {resp.status}")
                data = await resp.json()
                return data["translatedText"], data.get("detectedLanguage", "unknown")

    # -----------------------
    # Error handling helper
    # -----------------------
    async def send_error_embed_to_channel(self, message, user, original_text, error):
        guild_id = message.guild.id
        error_channel_id = await database.get_error_channel(guild_id)
        if error_channel_id:
            ch = message.guild.get_channel(error_channel_id)
            if ch:
                embed = discord.Embed(
                    title="❌ Translation Error",
                    description="An error occurred during translation.",
                    color=0xde002a
                )
                embed.add_field(name="User", value=f"{user} ({user.id})", inline=False)
                embed.add_field(name="Original Text", value=original_text[:1024], inline=False)
                embed.add_field(name="Channel", value=message.channel.mention, inline=False)
                embed.add_field(name="Error", value=str(error)[:1024], inline=False)
                embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
                await ch.send(embed=embed)
            else:
                print(f"❌ Error channel not found: {error_channel_id}")
        else:
            print(f"❌ Error: {error} | User: {user} | Text: {original_text}")

    async def send_error_embed(self, interaction, error, user=None, original_text=None):
        # For slash command errors
        try:
            embed = discord.Embed(
                title="❌ Translation Error",
                description="An error occurred during translation.",
                color=0xde002a
            )
            if user:
                embed.add_field(name="User", value=f"{user} ({user.id})", inline=False)
            if original_text:
                embed.add_field(name="Original Text", value=original_text[:1024], inline=False)
            embed.add_field(name="Error", value=str(error)[:1024], inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"❌ Failed to send slash error embed: {e}")


async def setup(bot):
    await bot.add_cog(Translate(bot))
