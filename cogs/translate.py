import discord
from discord.ext import commands
from discord import app_commands
from utils import database
import aiohttp
import datetime
from googletrans import Translator

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
            embed = self.create_embed(
                author=interaction.user,
                original_text=text,
                translated_text=translated_text,
                target_lang=target_lang,
                detected_lang=detected,
                timestamp=datetime.datetime.utcnow(),
                original_msg_url=None
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    # -----------------------
    # Reaction-to-translate logic
    # -----------------------
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        if str(reaction.emoji) != "🔃":
            return

        message = reaction.message
        guild_id = message.guild.id if message.guild else None
        channel_ids = await database.get_translation_channels(guild_id)

        if not (channel_ids and message.channel.id in channel_ids):
            return

        try:
            # Determine target language
            user_lang = await database.get_user_lang(user.id)
            target_lang = user_lang or await database.get_server_lang(guild_id) or "en"

            # Translate text
            translated_text, detected = await self.translate_text(message.content, target_lang)

            # Embed with author info and timestamp
            embed = self.create_embed(
                author=message.author,
                original_text=message.content,
                translated_text=translated_text,
                target_lang=target_lang,
                detected_lang=detected,
                timestamp=message.created_at,
                original_msg_url=message.jump_url
            )

            await user.send(embed=embed)
            await reaction.remove(user)
        except Exception as e:
            # Send to error channel in embed style
            error_channel_id = await database.get_error_channel(guild_id)
            if error_channel_id and message.guild:
                ch = message.guild.get_channel(error_channel_id)
                if ch:
                    embed = discord.Embed(
                        title="❌ Translation Error",
                        description=f"**User:** {user} (`{user.id}`)\n"
                                    f"**Original Message:** {message.content}\n"
                                    f"**Error:** {e}",
                        color=0xde002a,
                        timestamp=datetime.datetime.utcnow()
                    )
                    embed.set_footer(text="Translation attempt failed")
                    await ch.send(embed=embed)
            else:
                print(f"❌ Error: {e}")

    # -----------------------
    # Helper: Translate text via LibreTranslate → fallback Google
    # -----------------------
    async def translate_text(self, text: str, target_lang: str):
        # Try LibreTranslate first
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(LIBRE_URL, json={"q": text, "source": "auto", "target": target_lang}) as resp:
                    if resp.status != 200:
                        raise Exception(f"LibreTranslate returned status {resp.status}")
                    try:
                        data = await resp.json()
                        return data["translatedText"], data.get("detectedLanguage", "unknown")
                    except aiohttp.ContentTypeError:
                        raise Exception("LibreTranslate returned non-JSON response")
            except Exception:
                # Fallback to Google Translate
                google_result = self.google_translator.translate(text, dest=target_lang)
                detected = google_result.src or "unknown"
                return google_result.text, detected

    # -----------------------
    # Embed creator helper
    # -----------------------
    def create_embed(self, author, original_text, translated_text, target_lang, detected_lang, timestamp, original_msg_url=None):
        embed = discord.Embed(
            description=translated_text,
            color=0xde002a,
            timestamp=timestamp
        )
        embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)
        footer_text = f"Translated to: {target_lang} | Detected: {detected_lang}"
        embed.set_footer(text=footer_text)
        if original_msg_url:
            embed.add_field(name="\u200b", value=f"[Original message]({original_msg_url})", inline=False)
        return embed

async def setup(bot):
    await bot.add_cog(Translate(bot))
