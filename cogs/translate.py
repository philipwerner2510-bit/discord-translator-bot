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
    # Translate Slash Command
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
        if user.bot or not reaction.message.guild:
            return

        message = reaction.message
        guild_id = message.guild.id
        channel_ids = await database.get_translation_channels(guild_id)

        if channel_ids and message.channel.id in channel_ids and str(reaction.emoji) == "🔃":
            try:
                user_lang = await database.get_user_lang(user.id)
                target_lang = user_lang or await database.get_server_lang(guild_id)

                if not target_lang:
                    await user.send("❌ No language set. Use `/setmylang` or ask an admin to set a default.")
                    return

                translated_text, detected = await self.translate_text(message.content, target_lang)

                # Build embed with author info
                embed = discord.Embed(color=0xde002a)
                embed.set_author(
                    name=message.author.display_name,
                    icon_url=message.author.display_avatar.url if message.author.display_avatar else discord.Embed.Empty
                )
                embed.set_footer(text=f"Detected language: {detected} | Translated to: {target_lang}")

                await user.send(embed=embed)
                await user.send(translated_text)
                await reaction.remove(user)
            except Exception as e:
                error_channel = await database.get_error_channel(guild_id)
                if error_channel:
                    ch = message.guild.get_channel(error_channel)
                    if ch:
                        await ch.send(f"❌ Error while translating: {e}")
                else:
                    print(f"❌ Error: {e}")

    # -----------------------
    # Translation helper
    # -----------------------
    async def translate_text(self, text: str, target_lang: str):
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

async def setup(bot):
    await bot.add_cog(Translate(bot))
