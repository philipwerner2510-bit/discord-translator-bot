# cogs/translate.py
import re
import discord
from discord.ext import commands
from discord import app_commands
from utils import database
import aiohttp
from googletrans import Translator as GoogleTranslator
from datetime import datetime

LIBRE_URL = "https://libretranslate.de/translate"
CUSTOM_EMOJI_RE = re.compile(r"<(a?):([a-zA-Z0-9_]+):(\d+)>")  # groups: animated, name, id

# List of supported language codes (matches /langlist)
SUPPORTED_LANGS = [
    "en", "zh", "hi", "es", "fr", "ar", "bn", "pt", "ru", "ja",
    "de", "jv", "ko", "vi", "mr", "ta", "ur", "tr", "it", "th",
    "gu", "kn", "ml", "pa", "or", "fa", "sw", "am", "ha", "yo"
]

def normalize_emote_input(emote_str: str) -> str:
    """Return canonical string that matches str(reaction.emoji)."""
    return emote_str.strip()

def reaction_emoji_to_string(emoji):
    """Return a comparable string for reaction.emoji (works for unicode and PartialEmoji)."""
    return str(emoji)

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
        target_lang = target_lang.lower()

        if target_lang not in SUPPORTED_LANGS:
            await interaction.followup.send(f"❌ Unsupported language code `{target_lang}`.", ephemeral=True)
            return

        try:
            translated_text, detected = await self.translate_text(text, target_lang)

            embed = discord.Embed(
                description=translated_text,
                color=0xde002a
            )
            embed.set_author(
                name=interaction.user.display_name,
                icon_url=interaction.user.display_avatar.url
            )
            timestamp = datetime.utcnow().strftime("%H:%M UTC")
            embed.set_footer(text=f"Translated at {timestamp} | Language: {target_lang} | Detected: {detected}")

            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    # -----------------------
    # Add emote when a message is sent in a translation channel
    # -----------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        guild_id = message.guild.id
        channel_ids = await database.get_translation_channels(guild_id)
        if not channel_ids or message.channel.id not in channel_ids:
            return

        bot_emote_raw = await database.get_bot_emote(guild_id)
        bot_emote = normalize_emote_input(bot_emote_raw or "🔃")

        try:
            await message.add_reaction(bot_emote)
            return
        except Exception:
            pass

        m = CUSTOM_EMOJI_RE.match(bot_emote)
        if m:
            animated_flag, name, eid = m.groups()
            try:
                partial = discord.PartialEmoji(name=name, animated=bool(animated_flag), id=int(eid))
                await message.add_reaction(partial)
                return
            except Exception:
                pass

        print(f"⚠️ Could not add configured emote '{bot_emote}' in guild {guild_id}, channel {message.channel.id}")

    # -----------------------
    # React-to-translate logic
    # -----------------------
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user.bot:
            return

        message = reaction.message
        if message.guild is None:
            return

        guild_id = message.guild.id
        channel_ids = await database.get_translation_channels(guild_id)
        if not (channel_ids and message.channel.id in channel_ids):
            return

        bot_emote_raw = await database.get_bot_emote(guild_id) or "🔃"
        bot_emote = normalize_emote_input(bot_emote_raw)

        reacted = reaction_emoji_to_string(reaction.emoji)
        if reacted != bot_emote:
            return

        try:
            user_lang = await database.get_user_lang(user.id)
            target_lang = (user_lang or await database.get_server_lang(guild_id) or "en").lower()

            if target_lang not in SUPPORTED_LANGS:
                target_lang = "en"

            translated_text, detected = await self.translate_text(message.content or "", target_lang)

            embed = discord.Embed(
                description=translated_text,
                color=0xde002a
            )
            embed.set_author(
                name=message.author.display_name,
                icon_url=message.author.display_avatar.url
            )
            timestamp = message.created_at.strftime("%H:%M UTC")
            embed.set_footer(text=f"{timestamp} | Language: {target_lang} | Detected: {detected}")

            original_msg_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
            embed.description += f"\n[Original message]({original_msg_link})"

            await user.send(embed=embed)

            try:
                await reaction.remove(user)
            except Exception:
                pass

        except Exception as e:
            err_ch_id = await database.get_error_channel(guild_id)
            if err_ch_id:
                ch = message.guild.get_channel(err_ch_id)
                if ch:
                    err_embed = discord.Embed(title="❌ Translation Error", color=0xde002a)
                    err_embed.add_field(name="User", value=f"{user} (`{user.id}`)", inline=False)
                    err_embed.add_field(name="Original Text", value=(message.content or "—")[:1024], inline=False)
                    err_embed.add_field(name="Error", value=str(e), inline=False)
                    await ch.send(embed=err_embed)
                    return
            print(f"[Translate error][Guild {guild_id}] User {user.id} - {e}")

    # -----------------------
    # Helper: Translate text with LibreTranslate, fallback to Google
    # -----------------------
    async def translate_text(self, text: str, target_lang: str):
        if target_lang not in SUPPORTED_LANGS:
            raise ValueError(f"Unsupported language code: {target_lang}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    LIBRE_URL,
                    json={"q": text, "source": "auto", "target": target_lang},
                    headers={"Content-Type": "application/json"},
                    timeout=10
                ) as resp:
                    if resp.status != 200:
                        raise Exception(f"Translation API returned status {resp.status}")
                    data = await resp.json()
                    return data.get("translatedText", ""), data.get("detectedLanguage", "unknown")
        except Exception as e:
            print(f"⚠️ LibreTranslate failed: {e} — falling back to Google Translate")
            try:
                result = self.google_translator.translate(text, dest=target_lang)
                return result.text, result.src
            except Exception as ge:
                raise Exception(f"Both translation services failed: {ge}") from ge

async def setup(bot):
    await bot.add_cog(Translate(bot))
