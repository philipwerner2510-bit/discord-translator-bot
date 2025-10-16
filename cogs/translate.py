import discord
from discord.ext import commands
from discord import app_commands
from utils import database
import aiohttp
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
            translated_text, detected = await self.safe_translate(text, target_lang)

            embed = discord.Embed(
                title="🌐 Translation",
                description=translated_text,
                color=0xde002a
            )
            embed.set_footer(text=f"Detected: {detected} | Translated to: {target_lang}")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    # -----------------------
    # Reaction-to-translate logic
    # -----------------------
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        message = reaction.message
        guild_id = message.guild.id if message.guild else None
        if not guild_id:
            return

        channel_ids = await database.get_translation_channels(guild_id)
        bot_emote = await database.get_bot_emote(guild_id) or "🔃"

        if channel_ids and message.channel.id in channel_ids and str(reaction.emoji) == bot_emote:
            try:
                user_lang = await database.get_user_lang(user.id)
                target_lang = user_lang or await database.get_server_lang(guild_id) or "en"

                translated_text, detected = await self.safe_translate(message.content, target_lang)

                embed = discord.Embed(
                    color=0xde002a,
                    description=translated_text
                )
                embed.set_author(
                    name=message.author.display_name,
                    icon_url=message.author.display_avatar.url
                )
                timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
                embed.set_footer(
                    text=f"Translated at {timestamp} | Language: {target_lang} | Detected: {detected} | [Original message]({message.jump_url})"
                )

                await user.send(embed=embed)
                await reaction.remove(user)

            except Exception as e:
                error_channel_id = await database.get_error_channel(guild_id)
                if error_channel_id:
                    ch = message.guild.get_channel(error_channel_id)
                    if ch:
                        error_embed = discord.Embed(
                            title="❌ Translation Error",
                            color=0xde002a,
                            description=f"**User:** {user.mention}\n**Message:** {message.content[:200]}{'...' if len(message.content)>200 else ''}\n**Error:** {e}"
                        )
                        await ch.send(embed=error_embed)
                else:
                    print(f"❌ Error: {e}")

    # -----------------------
    # Safe translate: LibreTranslate first, fallback to Google
    # -----------------------
    async def safe_translate(self, text: str, target_lang: str):
        # Attempt LibreTranslate first
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(LIBRE_URL, json={"q": text, "source": "auto", "target": target_lang}) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["translatedText"], data.get("detectedLanguage", "unknown")
                    else:
                        raise Exception(f"LibreTranslate returned status {resp.status}")
        except Exception as e:
            # Fallback to Google Translate
            try:
                result = self.google_translator.translate(text, dest=target_lang)
                return result.text, result.src
            except Exception:
                raise Exception(f"Both LibreTranslate and Google Translate failed: {e}")

async def setup(bot):
    await bot.add_cog(Translate(bot))
