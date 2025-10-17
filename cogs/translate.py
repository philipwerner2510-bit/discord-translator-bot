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

def normalize_emote_input(emote_str: str) -> str:
    """Return canonical string that matches str(reaction.emoji)."""
    # If user passed a plain unicode emoji, use it as-is.
    # If user passed Discord custom emoji like <:name:id> or <a:name:id>, keep same string.
    return emote_str.strip()

def reaction_emoji_to_string(emoji):
    """Return a comparable string for reaction.emoji (works for unicode and PartialEmoji)."""
    # For unicode emoji, discord gives a str (e.g. "🔃")
    # For custom emojis, str(PartialEmoji) returns "<:name:id>" (or "<a:name:id>")
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
        # Ignore bots & DMs
        if message.author.bot or message.guild is None:
            return

        guild_id = message.guild.id
        channel_ids = await database.get_translation_channels(guild_id)
        if not channel_ids or message.channel.id not in channel_ids:
            return

        # Get configured emote (as stored string) or default
        bot_emote_raw = await database.get_bot_emote(guild_id)
        bot_emote = bot_emote_raw or "🔃"
        bot_emote = normalize_emote_input(bot_emote)

        # Try to add reaction. Handle unicode first; if fails, try parse custom emoji.
        try:
            await message.add_reaction(bot_emote)
            return
        except Exception:
            pass

        # Try to parse custom emoji like <:name:id> or <a:name:id>
        m = CUSTOM_EMOJI_RE.match(bot_emote)
        if m:
            animated_flag, name, eid = m.groups()
            try:
                partial = discord.PartialEmoji(name=name, animated=bool(animated_flag), id=int(eid))
                await message.add_reaction(partial)
                return
            except Exception:
                # fall through to logging
                pass

        # If we reached here, adding reaction failed (invalid emoji or missing perms)
        # Log for debugging but don't crash
        print(f"⚠️ Could not add configured emote '{bot_emote}' in guild {guild_id}, channel {message.channel.id}")

    # -----------------------
    # React-to-translate logic
    # -----------------------
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user.bot:
            return

        message = reaction.message
        # Ignore DMs
        if message.guild is None:
            return

        guild_id = message.guild.id
        channel_ids = await database.get_translation_channels(guild_id)
        if not (channel_ids and message.channel.id in channel_ids):
            return

        # Compare reaction emoji to configured emote (handle unicode & custom)
        bot_emote_raw = await database.get_bot_emote(guild_id) or "🔃"
        bot_emote = normalize_emote_input(bot_emote_raw)

        reacted = reaction_emoji_to_string(reaction.emoji)  # e.g. "🔃" or "<:name:id>"
        if reacted != bot_emote:
            return  # not our configured emote

        # Now proceed with translation and single embed send
        try:
            user_lang = await database.get_user_lang(user.id)
            target_lang = user_lang or await database.get_server_lang(guild_id) or "en"

            translated_text, detected = await self.translate_text(message.content or "", target_lang)

            # Build embed (single embed only)
            embed = discord.Embed(
                description=translated_text,
                color=0xde002a
            )
            embed.set_author(
                name=message.author.display_name,
                icon_url=message.author.display_avatar.url
            )
            timestamp = message.created_at.strftime("%H:%M UTC")
            embed.set_footer(text=f"Translated at {timestamp} | Language: {target_lang} | Detected: {detected}")

            # Original message hyperlink hidden behind "Original message"
            original_msg_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
            # Append as hidden link text at end of description (keeps it compact)
            embed.description = embed.description + f"\n[Original message]({original_msg_link})"

            # Send DM with only the embed (one message)
            await user.send(embed=embed)

            # Remove the reacting user's reaction (silent)
            try:
                await reaction.remove(user)
            except Exception:
                # ignore remove errors (missing perms)
                pass

        except Exception as e:
            # Send error embed to configured error channel with user + text
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
            # fallback to console
            print(f"[Translate error][Guild {guild_id}] User {user.id} - {e}")

    # -----------------------
    # Helper: Translate text with LibreTranslate, fallback to Google
    # -----------------------
    async def translate_text(self, text: str, target_lang: str):
        # Try LibreTranslate first
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
            # fallback to googletrans (local lib)
            print(f"⚠️ LibreTranslate failed: {e} — falling back to Google Translate")
            try:
                result = self.google_translator.translate(text, dest=target_lang)
                return result.text, result.src
            except Exception as ge:
                raise Exception(f"Both translation services failed: {ge}") from ge

async def setup(bot):
    await bot.add_cog(Translate(bot))
