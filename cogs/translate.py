import discord
from discord.ext import commands
from discord import app_commands
from utils import database
import aiohttp

LIBRE_URL = "https://libretranslate.de/translate"

class TranslateCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -----------------------
    # Manual /translate command
    # -----------------------
    @app_commands.command(name="translate", description="Translate a specific text manually.")
    async def translate(self, interaction: discord.Interaction, text: str, target_lang: str):
        await interaction.response.defer(ephemeral=True)
        try:
            translated_text, detected = await self.translate_text(text, target_lang)
            # Embed with detected/target language
            embed = discord.Embed(
                title="🌐 Translation",
                color=0xDE002A
            )
            embed.set_footer(text=f"Detected language: {detected} | Translated to: {target_lang}")
            await interaction.followup.send(embed=embed)
            await interaction.followup.send(translated_text)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    # -----------------------
    # Reaction translation
    # -----------------------
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        guild_id = reaction.message.guild.id if reaction.message.guild else None
        channel_ids = await database.get_translation_channels(guild_id)

        # Only react if in selected channels
        if channel_ids and reaction.message.channel.id in channel_ids:
            # Fetch the custom emote for this guild
            guild_emote = await database.get_guild_emote(guild_id)
            emoji_to_check = guild_emote or "🔃"

            if str(reaction.emoji) != emoji_to_check:
                return

            try:
                # Remove user's reaction immediately
                await reaction.remove(user)

                # Determine target language
                user_lang = await database.get_user_lang(user.id)
                target_lang = user_lang or await database.get_server_lang(guild_id)

                if not target_lang:
                    await user.send("❌ No language set. Use `/setmylang` or ask an admin to set a default.")
                    return

                translated_text, detected = await self.translate_text(reaction.message.content, target_lang)

                # Build embed
                embed = discord.Embed(color=0xDE002A)
                embed.set_author(
                    name=reaction.message.author.display_name,
                    icon_url=reaction.message.author.display_avatar.url
                    if reaction.message.author.display_avatar else discord.Embed.Empty
                )
                embed.set_footer(text=f"Detected language: {detected} | Translated to: {target_lang}")

                await user.send(embed=embed)
                await user.send(translated_text)
            except Exception as e:
                # Send error to guild error channel if set
                error_channel_id = await database.get_error_channel(guild_id)
                if error_channel_id:
                    ch = reaction.message.guild.get_channel(error_channel_id)
                    if ch:
                        await ch.send(f"❌ Error while translating: {e}")
                else:
                    print(f"[Guild {guild_id}] ❌ Error: {e}")

    # -----------------------
    # Helper: translate text via LibreTranslate
    # -----------------------
    async def translate_text(self, text: str, target_lang: str):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                LIBRE_URL,
                json={"q": text, "source": "auto", "target": target_lang}
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"LibreTranslate returned status {resp.status}")
                data = await resp.json()
                translated = data.get("translatedText")
                detected = data.get("detectedLanguage") or "unknown"
                return translated, detected


async def setup(bot):
    await bot.add_cog(TranslateCog(bot))
