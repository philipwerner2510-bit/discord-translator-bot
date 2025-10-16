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
            translated_text, detected = await self.try_translation(text, target_lang)
            embed = discord.Embed(
                title="🌐 Translation",
                description=translated_text,
                color=0xde002a
            )
            embed.set_footer(text=f"Detected: {detected} | Translated to: {target_lang} | Translated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
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

        if channel_ids and message.channel.id in channel_ids and str(reaction.emoji) == "🔃":
            try:
                # Determine user target language
                user_lang = await database.get_user_lang(user.id)
                target_lang = user_lang or await database.get_server_lang(guild_id) or "en"

                translated_text, detected = await self.try_translation(message.content, target_lang)

                # Embed
                embed = discord.Embed(
                    description=translated_text,
                    color=0xde002a
                )
                embed.set_author(
                    name=message.author.display_name,
                    icon_url=message.author.display_avatar.url
                )
                embed.set_footer(
                    text=f"Translated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC | Language: {target_lang} | Detected: {detected}"
                )

                # Add a small link to original message below embed
                original_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
                embed.add_field(name="Original message", value=f"[Click here]({original_link})", inline=False)

                await user.send(embed=embed)
                await reaction.remove(user)

            except Exception as e:
                error_channel_id = await database.get_error_channel(guild_id)
                if error_channel_id:
                    ch = message.guild.get_channel(error_channel_id)
                    if ch:
                        err_embed = discord.Embed(
                            title="❌ Translation Error",
                            color=0xde002a
                        )
                        err_embed.add_field(name="User", value=f"{user} ({user.id})", inline=False)
                        err_embed.add_field(name="Original Text", value=message.content or "No content", inline=False)
                        err_embed.add_field(name="Error", value=str(e), inline=False)
                        err_embed.set_footer(text=f"Channel: {message.channel.name}")
                        await ch.send(embed=err_embed)
                else:
                    print(f"❌ Error: {e}")

    # -----------------------
    # Try multiple translation engines
    # -----------------------
    async def try_translation(self, text: str, target_lang: str):
        # First try LibreTranslate
        try:
            return await self.translate_libre(text, target_lang)
        except Exception as e:
            print(f"LibreTranslate failed: {e}, falling back to Google")

        # Then try Google Translate
        try:
            return await self.translate_google(text, target_lang)
        except Exception as e:
            print(f"Google Translate failed: {e}")
            raise Exception("All translation services failed.")

    # -----------------------
    # LibreTranslate
    # -----------------------
    async def translate_libre(self, text: str, target_lang: str):
        async with aiohttp.ClientSession() as session:
            async with session.post(LIBRE_URL, json={"q": text, "source": "auto", "target": target_lang}) as resp:
                if resp.status != 200:
                    raise Exception(f"Translation API returned status {resp.status}")
                data = await resp.json()
                return data["translatedText"], data.get("detectedLanguage", "unknown")

    # -----------------------
    # Google Translate
    # -----------------------
    async def translate_google(self, text: str, target_lang: str):
        result = self.google_translator.translate(text, dest=target_lang)
        return result.text, result.src

async def setup(bot):
    await bot.add_cog(Translate(bot))
