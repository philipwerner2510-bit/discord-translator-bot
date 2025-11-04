# cogs/translate.py
import re
import discord
from discord.ext import commands
from discord import app_commands
from utils import database
from utils.cache import TranslationCache
from utils.config import SUPPORTED_LANGS, CONFIG
import aiohttp
from googletrans import Translator as GoogleTranslator
from datetime import datetime
import asyncio

LIBRE_URL = "https://libretranslate.de/translate"
CUSTOM_EMOJI_RE = re.compile(r"<(a?):([a-zA-Z0-9_]+):(\d+)>")

def normalize_emote_input(emote_str: str) -> str:
    return (emote_str or "").strip()

def reaction_emoji_to_string(emoji) -> str:
    return str(emoji)

def clamp(t: str, limit: int = 4000) -> str:
    return t if len(t) <= limit else t[: limit - 1] + "…"

class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.google_translator = GoogleTranslator()
        self.sent_translations = set()  # (message_id, user_id)
        self.cache = TranslationCache(ttl=CONFIG.reaction_timeout, max_entries=2000)
        self.http = aiohttp.ClientSession()

    def cog_unload(self):
        self.bot.loop.create_task(self.http.close())

    # -----------------------
    # Manual /translate
    # -----------------------
    @app_commands.guild_only()
    @app_commands.command(name="translate", description="Translate a specific text manually.")
    async def translate(self, interaction: discord.Interaction, text: str, target_lang: str):
        await interaction.response.defer(ephemeral=True)
        target_lang = target_lang.lower()
        if target_lang not in SUPPORTED_LANGS:
            await interaction.followup.send(
                f"❌ Unsupported language code `{target_lang}`.", ephemeral=True
            )
            return
        try:
            translated_text, detected = await self.translate_text(text, target_lang)
            embed = discord.Embed(description=clamp(translated_text), color=0xDE002A)
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            embed.set_footer(text=f"Translated at {timestamp} | Language: {target_lang} | Detected: {detected}")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    # -----------------------
    # Add bot emote to eligible messages
    # -----------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        guild_id = message.guild.id
        channel_ids = await database.get_translation_channels(guild_id)
        chan_id = message.channel.id
        parent_id = getattr(message.channel, "parent_id", None)
        eligible = chan_id in channel_ids or (parent_id and parent_id in channel_ids)
        if not eligible:
            return
        bot_emote = normalize_emote_input(await database.get_bot_emote(guild_id) or "🔃")
        try:
            await message.add_reaction(bot_emote)
        except Exception:
            m = CUSTOM_EMOJI_RE.match(bot_emote)
            if m:
                animated_flag, name, eid = m.groups()
                try:
                    partial = discord.PartialEmoji(name=name, animated=bool(animated_flag), id=int(eid))
                    await message.add_reaction(partial)
                except Exception:
                    print(f"⚠️ Could not add configured emote '{bot_emote}' in guild {guild_id}, channel {message.channel.id}")
            else:
                print(f"⚠️ Could not add configured emote '{bot_emote}' in guild {guild_id}, channel {message.channel.id}")

    # -----------------------
    # Raw reaction handler (works even if message not cached)
    # -----------------------
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        guild = self.bot.get_guild(payload.guild_id) if payload.guild_id else None
        if not guild:
            return
        channel = self.bot.get_channel(payload.channel_id) or await self.bot.fetch_channel(payload.channel_id)
        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return
        user = guild.get_member(payload.user_id) or await self.bot.fetch_user(payload.user_id)
        await self._handle_reaction(message, str(payload.emoji), user)

    # optional compatibility if other cogs call it
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user.bot or reaction.message.guild is None:
            return
        await self._handle_reaction(reaction.message, reaction_emoji_to_string(reaction.emoji), user)

    async def _handle_reaction(self, message: discord.Message, emoji_str: str, user: discord.abc.User):
        if message.guild is None:
            return
        guild_id = message.guild.id

        # eligible channel?
        channel_ids = await database.get_translation_channels(guild_id)
        chan_id = message.channel.id
        parent_id = getattr(message.channel, "parent_id", None)
        eligible = chan_id in channel_ids or (parent_id and parent_id in channel_ids)
        if not eligible:
            return

        # right emoji?
        bot_emote = normalize_emote_input(await database.get_bot_emote(guild_id) or "🔃")
        if emoji_str != bot_emote:
            return

        # dedupe AFTER checks
        key = (message.id, user.id)
        if key in self.sent_translations:
            return
        self.sent_translations.add(key)
        asyncio.create_task(self.clear_sent(key, delay=CONFIG.reaction_timeout))

        try:
            user_lang = await database.get_user_lang(user.id)
            target_lang = (user_lang or await database.get_server_lang(guild_id) or "en").lower()
            if target_lang not in SUPPORTED_LANGS:
                target_lang = "en"

            translated_text, detected = await self.translate_text(message.content or "", target_lang)
            embed = discord.Embed(description=clamp(translated_text), color=0xDE002A)
            embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M UTC")
            embed.set_footer(text=f"{timestamp} | Language: {target_lang} | Detected: {detected}")
            embed.description += f"\n[Original message](https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id})"

            try:
                await user.send(embed=embed)
            except discord.Forbidden:
                await message.channel.send(f"{user.mention} I couldn’t DM you (privacy settings).", delete_after=10)

            # stats
            self.bot.total_translations = getattr(self.bot, "total_translations", 0) + 1

            # be nice: remove user reaction if we can manage messages
            perms = message.channel.permissions_for(message.guild.me)
            if perms.manage_messages:
                try: await message.remove_reaction(emoji_str, user)
                except Exception: pass

        except Exception as e:
            err_ch_id = await database.get_error_channel(guild_id)
            if err_ch_id:
                ch = message.guild.get_channel(err_ch_id)
                if ch:
                    err_embed = discord.Embed(title="❌ Translation Error", color=0xDE002A)
                    err_embed.add_field(name="User", value=f"{user} (`{user.id}`)", inline=False)
                    err_embed.add_field(name="Original Text", value=(message.content or "—")[:1024], inline=False)
                    err_embed.add_field(name="Error", value=str(e), inline=False)
                    await ch.send(embed=err_embed)
            print(f"[Translate error][Guild {guild_id}] User {user.id} - {e}")

    async def clear_sent(self, key, delay: int):
        await asyncio.sleep(delay)
        self.sent_translations.discard(key)

    # -----------------------
    # Translate helper with cache (Libre first, Google fallback)
    # -----------------------
    async def translate_text(self, text: str, target_lang: str):
        if target_lang not in SUPPORTED_LANGS:
            raise ValueError(f"Unsupported language code: {target_lang}")

        async def compute():
            # Try LibreTranslate
            try:
                async with self.http.post(
                    LIBRE_URL,
                    json={"q": text, "source": "auto", "target": target_lang},
                    headers={"Content-Type": "application/json"},
                    timeout=10
                ) as resp:
                    if resp.status != 200:
                        raise Exception(f"LibreTranslate returned {resp.status}")
                    data = await resp.json()
                    det = data.get("detectedLanguage")
                    detected = det.get("language") if isinstance(det, dict) else (det or "unknown")
                    return data.get("translatedText", ""), detected or "unknown"
            except Exception as e:
                print(f"⚠️ LibreTranslate failed: {e} — falling back to Google Translate")

            # Fallback to Google Translate
            result = self.google_translator.translate(text, dest=target_lang)
            return result.text, result.src

        return await self.cache.get_or_set(text, target_lang, compute)

async def setup(bot):
    await bot.add_cog(Translate(bot))