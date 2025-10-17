import discord
from discord.ext import commands
from discord import app_commands
from utils import database
import aiohttp
from datetime import datetime

LIBRE_URL = "https://libretranslate.de/translate"

# Optional: import Google / Microsoft APIs if you configure API keys
# from googletrans import Translator as GoogleTranslator
# import ms_translation_api  # placeholder for Microsoft translation

class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # self.google_translator = GoogleTranslator()  # Uncomment if using Google API

    # -----------------------
    # Slash command: /translate
    # -----------------------
    @app_commands.command(name="translate", description="Translate a specific text manually.")
    async def translate(self, interaction: discord.Interaction, text: str, target_lang: str):
        await interaction.response.defer(ephemeral=True)
        try:
            translated_text, detected = await self.try_translation(text, target_lang)
            embed = self.build_embed(interaction.user, text, translated_text, target_lang, detected, None)
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
                user_lang = await database.get_user_lang(user.id)
                target_lang = user_lang or await database.get_server_lang(guild_id) or "en"

                translated_text, detected = await self.try_translation(message.content, target_lang)

                # Build embed
                embed = self.build_embed(
                    message.author,
                    message.content,
                    translated_text,
                    target_lang,
                    detected,
                    message.jump_url,
                    message.created_at
                )

                # Send only once
                await user.send(embed=embed)
                await reaction.remove(user)

            except Exception as e:
                error_channel_id = await database.get_error_channel(guild_id)
                if error_channel_id and message.guild:
                    ch = message.guild.get_channel(error_channel_id)
                    if ch:
                        error_embed = discord.Embed(
                            title="❌ Translation Error",
                            color=0xde002a,
                            timestamp=datetime.utcnow()
                        )
                        error_embed.add_field(name="User", value=f"{user} (`{user.id}`)", inline=False)
                        error_embed.add_field(name="Original Text", value=message.content, inline=False)
                        error_embed.add_field(name="Error", value=str(e), inline=False)
                        await ch.send(embed=error_embed)
                else:
                    print(f"❌ Error: {e}")

    # -----------------------
    # Helper: Build embed
    # -----------------------
    def build_embed(self, author, original_text, translated_text, target_lang, detected, jump_url=None, timestamp=None):
        embed = discord.Embed(
            description=translated_text,
            color=0xde002a,
            timestamp=timestamp
        )
        embed.set_author(
            name=author.display_name,
            icon_url=author.display_avatar.url
        )
        embed.set_footer(text=f"Language: {target_lang} | Detected: {detected}")
        if jump_url:
            embed.add_field(name="Original message", value=f"[Click here]({jump_url})", inline=False)
        return embed

    # -----------------------
    # Helper: Try translation with fallback
    # -----------------------
    async def try_translation(self, text: str, target_lang: str):
        # Try LibreTranslate first
        try:
            translated_text, detected = await self.translate_libre(text, target_lang)
            return translated_text, detected
        except Exception:
            # Optional fallback: Google Translate
            try:
                translated_text, detected = await self.translate_google(text, target_lang)
                return translated_text, detected
            except Exception:
                # Optional fallback: Microsoft Translate
                translated_text, detected = await self.translate_microsoft(text, target_lang)
                return translated_text, detected

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
    # Google Translate (placeholder, requires setup)
    # -----------------------
    async def translate_google(self, text: str, target_lang: str):
        # Example using googletrans
        from googletrans import Translator
        translator = Translator()
        result = translator.translate(text, dest=target_lang)
        return result.text, result.src

    # -----------------------
    # Microsoft Translate (placeholder, requires API key)
    # -----------------------
    async def translate_microsoft(self, text: str, target_lang: str):
        # Implement Microsoft Translate API call here
        # For now, just fallback returns original text
        return text, "unknown"

async def setup(bot):
    await bot.add_cog(Translate(bot))
