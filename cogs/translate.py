import discord
from discord.ext import commands
from discord import app_commands
from utils import database
import aiohttp
from googletrans import Translator as GoogleTranslator

LIBRE_URL = "https://libretranslate.de/translate"

class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.google_translator = GoogleTranslator()

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
            embed.add_field(name="Original Text", value=text[:1024], inline=False)
            embed.add_field(name="Translated Text", value=translated_text[:1024], inline=False)
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

        if not (channel_ids and message.channel.id in channel_ids):
            return

        bot_emote = await database.get_bot_emote(guild_id) or "🔃"
        if str(reaction.emoji) != bot_emote:
            return

        try:
            user_lang = await database.get_user_lang(user.id)
            target_lang = user_lang or await database.get_server_lang(guild_id) or "en"

            translated_text, detected = await self.translate_text(message.content, target_lang)

            # Minimal DM embed
            embed = discord.Embed(color=0xde002a)
            embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
            embed.add_field(name="Original Text", value=(message.content or "")[:1024], inline=False)
            embed.add_field(name="Translated Text", value=(translated_text or "")[:1024], inline=False)

            # Minimal footer with timestamp and jump link
            guild_name = message.guild.name if message.guild else "DM"
            channel_name = message.channel.name if hasattr(message.channel, "name") else "DM"
            msg_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}" if message.guild else ""
            footer_text = f"{guild_name} • #{channel_name}"
            if msg_link:
                footer_text += f" • [Jump to message]({msg_link})"

            embed.set_footer(text=footer_text)
            embed.timestamp = message.created_at

            await user.send(embed=embed)
            await reaction.remove(user)

        except Exception as e:
            # Send error embed to selected error channel
            error_channel_id = await database.get_error_channel(guild_id)
            if error_channel_id:
                ch = message.guild.get_channel(error_channel_id) if message.guild else None
                if ch:
                    err_embed = discord.Embed(title="❌ Translation Error", color=0xde002a)
                    err_embed.add_field(name="User", value=f"{user} ({user.id})", inline=False)
                    err_embed.add_field(name="Original Text", value=(message.content or "")[:1024], inline=False)
                    err_embed.add_field(name="Target Lang", value=target_lang, inline=False)
                    err_embed.add_field(name="Error", value=str(e), inline=False)
                    # Footer with minimal info
                    err_embed.set_footer(text=footer_text)
                    err_embed.timestamp = message.created_at
                    await ch.send(embed=err_embed)
            else:
                print(f"❌ Error: {e}")

    # -----------------------
    # Helper: Translate text via multiple free-tier engines
    # -----------------------
    async def translate_text(self, text: str, target_lang: str):
        # Try LibreTranslate first
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(LIBRE_URL, json={"q": text, "source": "auto", "target": target_lang}) as resp:
                    if resp.status != 200:
                        raise Exception(f"Translation API returned status {resp.status}")
                    data = await resp.json()
                    return data["translatedText"], data.get("detectedLanguage", "unknown")
        except Exception:
            # Fallback: Google Translate
            try:
                translated = self.google_translator.translate(text, dest=target_lang)
                return translated.text, translated.src
            except Exception:
                # Could add Microsoft Translator here if needed
                raise Exception("All free translation engines failed.")

async def setup(bot):
    await bot.add_cog(Translate(bot))
