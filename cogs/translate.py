# cogs/translate.py
import re
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import asyncio
import aiohttp
from googletrans import Translator as GoogleTranslator

from utils import database
from utils.cache import TranslationCache
from utils.logging_utils import log_error
from utils.config import SUPPORTED_LANGS, LANG_META, lang_label

CACHE = TranslationCache(ttl=300)
LIBRE_URL = "https://libretranslate.de/translate"

CUSTOM_EMOJI_RE = re.compile(r"<(a?):([a-zA-Z0-9_]+):(\d+)>")


def chunk_list(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def parse_partial_emoji(emote_str: str):
    m = CUSTOM_EMOJI_RE.match(str(emote_str))
    if not m:
        return None
    a, name, eid = m.groups()
    try:
        return discord.PartialEmoji(name=name, animated=bool(a), id=int(eid))
    except Exception:
        return None


class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.google = GoogleTranslator()
        self.processing = set()

    # --------------------------
    # Manual /translate
    # --------------------------
    @app_commands.command(name="translate", description="Translate text manually.")
    @app_commands.describe(text="Message to translate", target_lang="2-letter language code")
    async def cmd_translate(self, interaction: discord.Interaction, text: str, target_lang: str):
        await interaction.response.defer(ephemeral=True)
        target_lang = (target_lang or "").lower()
        if target_lang not in SUPPORTED_LANGS:
            supported = ", ".join(SUPPORTED_LANGS)
            return await interaction.followup.send(
                f"❌ Unsupported language `{target_lang}`.\nSupported: {supported}",
                ephemeral=True
            )
        translated, detected = await self.do_translate(text, target_lang)
        emb = discord.Embed(description=translated, color=0xDE002A)
        emb.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        emb.set_footer(text=f"Detected: {detected} | {datetime.utcnow():%H:%M UTC}")
        await interaction.followup.send(embed=emb, ephemeral=True)

    # --------------------------
    # Auto add reaction in selected channels (threads/forum friendly)
    # --------------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        guild = message.guild
        gid = guild.id

        parent = getattr(message.channel, "parent_id", None)
        route_channel_id = parent or message.channel.id

        try:
            allowed = await database.get_translation_channels(gid)
        except Exception as e:
            return await log_error(self.bot, gid, "DB error Channels", e, admin_notify=True)

        if not allowed or route_channel_id not in allowed:
            return

        me = guild.me
        perms = message.channel.permissions_for(me)
        if not (perms.add_reactions and perms.read_message_history and perms.view_channel):
            return await log_error(
                self.bot, gid,
                f"Missing reaction perms in #{message.channel.name} (AddReactions/ReadHistory/ViewChannel)",
                admin_notify=True
            )

        emote = await database.get_bot_emote(gid) or "🔃"

        async def try_add(em):
            try:
                await message.add_reaction(em)
                return True
            except Exception:
                pe = parse_partial_emoji(em)
                if not pe:
                    return False
                try:
                    await message.add_reaction(pe)
                    return True
                except Exception:
                    return False

        ok = await try_add(emote)
        if not ok and emote != "🔃":
            await try_add("🔃")

    # --------------------------
    # Reaction flow: translate or prompt picker
    # --------------------------
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user.bot or reaction.message.author.bot or not reaction.message.guild:
            return

        key = (reaction.message.id, user.id)
        if key in self.processing:
            return
        self.processing.add(key)
        await asyncio.sleep(0.1)

        try:
            await self.handle_reaction(reaction, user)
        except Exception as e:
            await log_error(self.bot, reaction.message.guild.id, "Reaction handler error", e, admin_notify=True)
        finally:
            self.processing.discard(key)

    async def handle_reaction(self, reaction, user):
        msg = reaction.message
        guild = msg.guild
        gid = guild.id

        parent = getattr(msg.channel, "parent_id", None)
        cid = parent or msg.channel.id

        allowed = await database.get_translation_channels(gid)
        if not allowed or cid not in allowed:
            return

        configured = await database.get_bot_emote(gid) or "🔃"
        if str(reaction.emoji) != configured:
            return

        # If user already has a language, translate immediately
        user_lang = await database.get_user_lang(user.id)
        if user_lang and user_lang.lower() in SUPPORTED_LANGS:
            await self.send_translation(msg, user, user_lang.lower(), configured)
            return

        # Otherwise show a modern, paginated picker
        try:
            await self.prompt_language_choice(msg, user)
        except discord.Forbidden:
            return await msg.channel.send(f"⚠️ I can’t DM {user.mention}. (Privacy settings)", delete_after=6)
        except Exception as e:
            await log_error(self.bot, gid, "Prompt send failed", e, admin_notify=True)

    # --------------------------
    # Modern paginated language picker (flags + names)
    # --------------------------
    async def prompt_language_choice(self, msg: discord.Message, user: discord.User):
        PER_PAGE = 25
        codes_sorted = list(SUPPORTED_LANGS)
        # stable, alphabetic by language name
        codes_sorted.sort(key=lambda c: LANG_META.get(c, ("🌐", c.upper()))[1])
        pages = list(chunk_list(codes_sorted, PER_PAGE))
        total_pages = len(pages)

        class LangView(discord.ui.View):
            def __init__(self, outer, message, requester, page_idx=0):
                super().__init__(timeout=60)
                self.outer = outer
                self.msg = message
                self.user = requester
                self.page_idx = page_idx
                self._rebuild()

            def _rebuild(self):
                self.clear_items()

                current_codes = pages[self.page_idx]
                placeholder = f"Choose language — Page {self.page_idx + 1}/{total_pages}"

                # Build pretty options
                options = [
                    discord.SelectOption(
                        label=lang_label(code)[:100],  # label limit
                        value=code,
                        description=f"Code: {code}"  # optional, ≤100 chars
                    )
                    for code in current_codes
                ]

                select = discord.ui.Select(
                    placeholder=placeholder,
                    min_values=1,
                    max_values=1,
                    options=options
                )

                async def on_select(inter: discord.Interaction):
                    if inter.user.id != self.user.id:
                        return await inter.response.defer()
                    lang = select.values[0]
                    await inter.response.defer(ephemeral=True)
                    try:
                        await database.set_user_lang(self.user.id, lang)
                    except Exception:
                        pass
                    await self.outer.send_translation(self.msg, self.user, lang)
                    self.stop()

                select.callback = on_select
                self.add_item(select)

                # Pagination controls
                if total_pages > 1:
                    prev_disabled = self.page_idx == 0
                    next_disabled = self.page_idx >= total_pages - 1

                    @discord.ui.button(label="⬅ Previous", style=discord.ButtonStyle.secondary, disabled=prev_disabled)
                    async def prev_btn(inter: discord.Interaction, button: discord.ui.Button):
                        if inter.user.id != self.user.id:
                            return await inter.response.defer()
                        self.page_idx -= 1
                        self._rebuild()
                        await inter.response.edit_message(content=self._content_text(), view=self)

                    @discord.ui.button(label="Next ➡", style=discord.ButtonStyle.primary, disabled=next_disabled)
                    async def next_btn(inter: discord.Interaction, button: discord.ui.Button):
                        if inter.user.id != self.user.id:
                            return await inter.response.defer()
                        self.page_idx += 1
                        self._rebuild()
                        await inter.response.edit_message(content=self._content_text(), view=self)

            def _content_text(self):
                preview = (self.msg.content or "").strip()
                if len(preview) > 120:
                    preview = preview[:117] + "…"
                return f"Pick a translation language for:\n> {preview}"

        temp = LangView(self, msg, user)
        await user.send(
            content=temp._content_text(),
            view=LangView(self, msg, user)
        )

    # --------------------------
    # Perform + DM translation (+ cleanup reaction)
    # --------------------------
    async def send_translation(self, msg: discord.Message, user: discord.User, target: str, configured_emote: str = None):
        text = msg.content or ""
        translated, detected = await self.do_translate(text, target)

        flag, name = LANG_META.get(target, ("🌐", target.upper()))
        title = f"{flag} {name} ({target})"

        emb = discord.Embed(description=translated, color=0xDE002A)
        emb.set_author(name=msg.author.display_name, icon_url=msg.author.display_avatar.url)
        emb.add_field(name="Original", value=f"[Jump to message]({msg.jump_url})", inline=False)
        emb.set_footer(text=f"{msg.created_at:%H:%M UTC} | to {title} • from {detected}")

        try:
            await user.send(embed=emb)
        except discord.Forbidden:
            try:
                await msg.channel.send(f"⚠️ I can’t DM {user.mention}. (Privacy settings)", delete_after=8)
            except Exception:
                pass

        # Stats
        try:
            await database.increment_user_counter(user.id, 1)
            await database.increment_guild_counter(msg.guild.id, 1)
        except Exception as e:
            await log_error(self.bot, msg.guild.id, "Stats increment failed", e, admin_notify=False)
        self.bot.total_translations += 1

        # Remove user's reaction if we can
        try:
            perms = msg.channel.permissions_for(msg.guild.me)
            if perms.manage_messages:
                if configured_emote is None:
                    configured_emote = await database.get_bot_emote(msg.guild.id) or "🔃"
                pe = parse_partial_emoji(configured_emote)
                await msg.remove_reaction(pe or configured_emote, user)
        except Exception:
            pass

    # --------------------------
    # Translation (cache + fallback)
    # --------------------------
    async def do_translate(self, text: str, target: str):
        if not text:
            return "—", "unknown"

        cached = await CACHE.get(text, target)
        if cached:
            return cached[0], cached[1]

        # Try LibreTranslate first
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    LIBRE_URL,
                    json={"q": text, "source": "auto", "target": target},
                    timeout=10
                ) as r:
                    if r.status == 200:
                        data = await r.json()
                        out = data.get("translatedText", "")
                        src = data.get("detectedLanguage", "auto")
                        await CACHE.set(text, target, (out, src))
                        return out, src
        except Exception:
            pass

        # Google fallback
        try:
            res = self.google.translate(text, dest=target)
            out = res.text
            src = res.src
            await CACHE.set(text, target, (out, src))
            return out, src
        except Exception:
            return text, "unknown"


async def setup(bot):
    await bot.add_cog(Translate(bot))