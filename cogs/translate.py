import discord
from discord.ext import commands
from discord import app_commands
from utils import database
import aiohttp

LIBRE_URL = "https://libretranslate.de/translate"

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
            translated_text, detected = await self.translate_text(text, target_lang)
            embed = discord.Embed(
                title="🌐 Translation",
                color=0xde002a
            )
            embed.set_footer(text=f"Detected language: {detected} | Translated to: {target_lang}")
            await interaction.followup.send(embed=embed)
            await interaction.followup.send(translated_text)
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

        # Only react if it's in a selected channel and emoji is 🔃
        if channel_ids and message.channel.id in channel_ids and str(reaction.emoji) == "🔃":
            try:
                user_lang = await database.get_user_lang(user.id)
                target_lang = user_lang or await database.get_server_lang(guild_id) or "en"

                translated_text, detected = await self.translate_text(message.content, target_lang)

                # Embed with author info
                embed = discord.Embed(color=0xde002a)
                embed.set_author(
                    name=message.author.display_name,
                    icon_url=message.author.display_avatar.url
                )
                embed.set_footer(text=f"Translated from {message.content[:50]}... | Language: {target_lang}")

                await user.send(embed=embed)
                await user.send(translated_text)
                await reaction.remove(user)
            except Exception as e:
                error_channel_id = await database.get_error_channel(guild_id)
                if error_channel_id:
                    ch = message.guild.get_channel(error_channel_id)
                    if ch:
                        await ch.send(f"❌ Error while translating: {e}")
                else:
                    print(f"❌ Error: {e}")

    # -----------------------
    # Helper: Translate text via public LibreTranslate
    # -----------------------
    async def translate_text(self, text: str, target_lang: str):
        async with aiohttp.ClientSession() as session:
            async with session.post(LIBRE_URL, json={"q": text, "source": "auto", "target": target_lang}) as resp:
                data = await resp.json()
                return data["translatedText"], data.get("detectedLanguage", "unknown")

async def setup(bot):
    await bot.add_cog(Translate(bot))
