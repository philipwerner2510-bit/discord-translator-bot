import discord
from discord.ext import commands
from discord import app_commands
from utils import database
import aiohttp
from googletrans import Translator
from datetime import datetime

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
            translated_text, detected = await self.translate_text(text, target_lang)
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

        # Only react if it's in a selected channel and emoji is the bot's emote or default 🔃
        bot_emote = await database.get_bot_emote(guild_id) or "🔃"
        if channel_ids and message.channel.id in channel_ids and str(reaction.emoji) == bot_emote:
            try:
                user_lang = await database.get_user_lang(user.id)
                target_lang = user_lang or await database.get_server_lang(guild_id) or "en"

                translated_text, detected = await self.translate_text(message.content, target_lang)

                # Create embed
                embed = discord.Embed(
                    description=translated_text,
                    color=0xde002a
                )
                embed.set_author(
                    name=message.author.display_name,
                    icon_url=message.author.display_avatar.url
                )
                timestamp_str = message.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
                embed.set_footer(text=f"Translated at {timestamp_str} | Language: {target_lang} | Detected: {detected}")

                # DM user with embed only
                dm_channel = user.dm_channel or await user.create_dm()
                await dm_channel.send(embed=embed)

                # Add original message link underneath
                original_link = f"[Original message]({message.jump_url})"
                await dm_channel.send(original_link)

                # Remove user's reaction
                await reaction.remove(user)

            except Exception as e:
                # Send embed-styled error to error channel
                error_channel_id = await database.get_error_channel(guild_id)
                if error_channel_id:
                    ch = message.guild.get_channel(error_channel_id)
                    if ch:
                        error_embed = discord.Embed(
                            title="❌ Translation Error",
                            color=0xde002a,
                            description=f"**User:** {user} (`{user.id}`)\n**Message:** {message.content}\n**Error:** {e}"
                        )
                        await ch.send(embed=error_embed)
                else:
                    print(f"❌ Error: {e}")

    # -----------------------
    # Helper: Translate text via LibreTranslate with Google fallback
    # -----------------------
    async def translate_text(self, text: str, target_lang: str):
        # Try LibreTranslate first
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    LIBRE_URL,
                    json={"q": text, "source": "auto", "target": target_lang},
                    headers={"Content-Type": "application/json"}
                ) as resp:
                    if resp.status != 200:
                        raise Exception(f"Translation API returned status {resp.status}")
                    data = await resp.json()
                    return data["translatedText"], data.get("detectedLanguage", "unknown")
        except Exception as libre_error:
            # Fallback to Google Translate
            try:
                result = self.google_translator.translate(text, dest=target_lang)
                return result.text, result.src
            except Exception as google_error:
                raise Exception(f"LibreTranslate failed: {libre_error}\nGoogle Translate failed: {google_error}")

async def setup(bot):
    await bot.add_cog(Translate(bot))
