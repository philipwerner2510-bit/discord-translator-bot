import discord
from discord.ext import commands
from discord import app_commands
from utils import database
import aiohttp

# Update this to a more reliable LibreTranslate endpoint or self-hosted URL
LIBRE_URL = "https://libretranslate.com/translate"

class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -----------------------
    # Slash command: /translate
    # -----------------------
    @app_commands.command(name="translate", description="Translate a specific text manually.")
    async def translate(self, interaction: discord.Interaction, text: str, target_lang: str):
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException:
            # Already deferred/acknowledged
            pass

        try:
            translated_text, detected = await self.translate_text(text, target_lang)
            embed = discord.Embed(
                title="🌐 Translation",
                color=0xde002a
            )
            embed.add_field(name="Translated Text", value=translated_text, inline=False)
            embed.set_footer(text=f"Detected language: {detected} | Translated to: {target_lang}")
            await interaction.followup.send(embed=embed, ephemeral=True)
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
        if not guild_id:
            return

        channel_ids = await database.get_translation_channels(guild_id)
        bot_emote = await database.get_bot_emote(guild_id) or "🔃"

        if channel_ids and message.channel.id in channel_ids and str(reaction.emoji) == bot_emote:
            try:
                user_lang = await database.get_user_lang(user.id)
                target_lang = user_lang or await database.get_server_lang(guild_id) or "en"

                translated_text, detected = await self.translate_text(message.content, target_lang)

                embed = discord.Embed(color=0xde002a)
                embed.set_author(
                    name=message.author.display_name,
                    icon_url=message.author.display_avatar.url
                )
                embed.add_field(name="Translated Text", value=translated_text, inline=False)
                embed.set_footer(text=f"From: {message.content[:50]}... | Language: {target_lang}")

                try:
                    await user.send(embed=embed)
                except discord.Forbidden:
                    # User DMs closed
                    error_channel_id = await database.get_error_channel(guild_id)
                    if error_channel_id:
                        ch = message.guild.get_channel(error_channel_id)
                        if ch:
                            await ch.send(f"❌ Could not DM user {user.mention} for translation.")

                # Remove reaction after translation
                try:
                    await reaction.remove(user)
                except discord.Forbidden:
                    print(f"Cannot remove reaction in #{message.channel.name}")

            except Exception as e:
                error_channel_id = await database.get_error_channel(guild_id)
                if error_channel_id:
                    ch = message.guild.get_channel(error_channel_id)
                    if ch:
                        await ch.send(f"❌ Error while translating: {e}")
                else:
                    print(f"❌ Error: {e}")

    # -----------------------
    # Helper: Translate text via LibreTranslate
    # -----------------------
    async def translate_text(self, text: str, target_lang: str):
        async with aiohttp.ClientSession() as session:
            headers = {"Content-Type": "application/json"}
            payload = {"q": text, "source": "auto", "target": target_lang}

            async with session.post(LIBRE_URL, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    raise Exception(f"Translation API returned status {resp.status}")
                try:
                    data = await resp.json()
                except Exception:
                    text = await resp.text()
                    raise Exception(f"Failed to parse translation response. Raw: {text[:200]}...")

                return data["translatedText"], data.get("detectedLanguage", "unknown")

async def setup(bot):
    await bot.add_cog(Translate(bot))
