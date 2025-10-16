# cogs/translate.py
import discord
from discord.ext import commands
from discord import app_commands
from utils import database
from googletrans import Translator
import aiohttp
import html
import aiosqlite
import asyncio

LIBRE_URL = "https://libretranslate.de/translate"
DB_PATH = "bot_data.db"

translator = Translator()

class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = asyncio.Queue()
        self.bot.loop.create_task(self.process_queue())
        self.bot.loop.create_task(self.init_cache_table())

    async def init_cache_table(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
            CREATE TABLE IF NOT EXISTS translation_cache(
                text TEXT,
                target_lang TEXT,
                translated TEXT,
                detected_lang TEXT,
                PRIMARY KEY(text, target_lang)
            )
            """)
            await db.commit()

    # -----------------------
    # Slash command: /translate
    # -----------------------
    @app_commands.command(name="translate", description="Translate a specific text manually.")
    async def translate(self, interaction: discord.Interaction, text: str, target_lang: str):
        await interaction.response.defer(ephemeral=True)
        await self.queue.put((interaction, text, target_lang))

    # NOTE: on_reaction_add listener intentionally removed from here to avoid duplicate handling.
    # events.py will delegate reactions to this public handler:
    async def handle_reaction(self, reaction: discord.Reaction, user: discord.User):
        """Public method called by events.py to process reaction translations."""
        # same logic that used to be in on_reaction_add
        if user.bot:
            return
        message = reaction.message
        guild_id = message.guild.id if message.guild else None
        if not guild_id:
            return

        channel_ids = await database.get_translation_channels(guild_id)
        bot_emote = await database.get_bot_emote(guild_id) or "🔃"

        if not (channel_ids and message.channel.id in channel_ids and str(reaction.emoji) == bot_emote):
            return

        # Put into queue for unified processing (so slash & reaction use same pipeline)
        await self.queue.put((user, message.content, None, True, guild_id, message, reaction))

    # -----------------------
    # Queue processor
    # -----------------------
    async def process_queue(self):
        while True:
            item = await self.queue.get()
            try:
                # Slash command tuple: (interaction, text, target_lang)
                if isinstance(item[0], discord.Interaction):
                    interaction, text, target_lang = item
                    translated_text, detected = await self.try_translate(text, target_lang)
                    embed = discord.Embed(title="🌐 Translation", color=0xde002a)
                    embed.add_field(name="Original Text", value=text, inline=False)
                    embed.add_field(name="Translated Text", value=translated_text, inline=False)
                    embed.set_footer(text=f"Detected language: {detected} | Translated to: {target_lang}")
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    # Reaction translation tuple:
                    # (user, text, target_lang (None), True, guild_id, message, reaction)
                    user, text, _, _, guild_id, message, reaction = item
                    # determine target_lang (user override or server default)
                    user_lang = await database.get_user_lang(user.id)
                    target_lang = user_lang or await database.get_server_lang(guild_id) or "en"

                    translated_text, detected = await self.try_translate(text, target_lang)

                    embed = discord.Embed(color=0xde002a)
                    embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
                    embed.add_field(name="Original Text", value=(message.content or "")[:1024], inline=False)
                    embed.add_field(name="Translated Text", value=(translated_text or "")[:1024], inline=False)
                    embed.set_footer(text=f"Detected language: {detected} | Translated to: {target_lang}")

                    # send DM once
                    try:
                        await user.send(embed=embed)
                        await user.send(translated_text)
                    except discord.Forbidden:
                        # user closed DMs — log to error channel if present
                        error_channel_id = await database.get_error_channel(guild_id)
                        if error_channel_id:
                            ch = message.guild.get_channel(error_channel_id)
                            if ch:
                                err_embed = discord.Embed(title="❌ Translation Error (DM failed)", color=0xde002a)
                                err_embed.add_field(name="User", value=f"{user} ({user.id})", inline=False)
                                err_embed.add_field(name="Original Text", value=(message.content or "")[:1024], inline=False)
                                err_embed.add_field(name="Target Lang", value=target_lang, inline=False)
                                err_embed.add_field(name="Note", value="Could not DM user (DMs closed).", inline=False)
                                await ch.send(embed=err_embed)
                    # remove reaction once
                    try:
                        await reaction.remove(user)
                    except discord.Forbidden:
                        # lack permission to remove reactions
                        pass

            except Exception as e:
                # Unified error handling for queue items
                if isinstance(item[0], discord.Interaction):
                    interaction = item[0]
                    try:
                        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
                    except Exception:
                        print(f"Failed to notify interaction of error: {e}")
                else:
                    user, text, _, _, guild_id, message, reaction = item
                    error_channel_id = await database.get_error_channel(guild_id)
                    if error_channel_id:
                        ch = message.guild.get_channel(error_channel_id)
                        if ch:
                            err_embed = discord.Embed(title="❌ Translation Error", color=0xde002a)
                            err_embed.add_field(name="User", value=f"{user} ({user.id})", inline=False)
                            err_embed.add_field(name="Original Text", value=(text or "")[:1024], inline=False)
                            err_embed.add_field(name="Channel", value=message.channel.mention, inline=False)
                            err_embed.add_field(name="Error", value=str(e)[:1024], inline=False)
                            err_embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
                            await ch.send(embed=err_embed)
                    else:
                        print(f"❌ Error processing translation: {e}")
            finally:
                self.queue.task_done()

    # -----------------------
    # Try translate with cache + fallback (simple: Libre -> Google)
    # -----------------------
    async def try_translate(self, text: str, target_lang: str):
        # Use cache table if present (optional). For brevity, call direct translation here.
        # Try LibreTranslate
        try:
            return await self.libre_translate(text, target_lang)
        except Exception as e:
            # fallback to googletrans
            try:
                res = translator.translate(text, dest=target_lang)
                return html.unescape(res.text), res.src
            except Exception as e2:
                raise Exception(f"All translation engines failed: {e2}")

    async def libre_translate(self, text: str, target_lang: str):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                LIBRE_URL,
                json={"q": text, "source": "auto", "target": target_lang, "format": "text"},
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"Translation API returned status {resp.status}")
                data = await resp.json(content_type=None)
                return data.get("translatedText", ""), data.get("detectedLanguage", "unknown")


async def setup(bot):
    await bot.add_cog(Translate(bot))
