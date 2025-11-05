# cogs/translate.py
import re
import asyncio
from datetime import datetime
import discord
from discord.ext import commands
from discord import app_commands
from utils import database
import os

from openai import OpenAI

# ---------- Config ----------
AI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

SUPPORTED_LANGS = [
    "en","zh","hi","es","fr","ar","bn","pt","ru","ja",
    "de","jv","ko","vi","mr","ta","ur","tr","it","th",
    "gu","kn","ml","pa","or","fa","sw","am","ha","yo"
]

CUSTOM_EMOJI_RE = re.compile(r"<(a?):([a-zA-Z0-9_]+):(\d+)>")  # <:name:id> or <a:name:id>

def normalize_emote_input(s: str) -> str:
    return (s or "").strip()

def emoji_to_str(emoji) -> str:
    # e.g. returns "👍" or "<:name:123>" for custom
    return str(emoji)

def same_reaction(a: str, b: str) -> bool:
    # Normalize custom forms to canonical strings
    if a == b:
        return True
    ma, mb = CUSTOM_EMOJI_RE.match(a or ""), CUSTOM_EMOJI_RE.match(b or "")
    if ma and mb:
        return ma.group(3) == mb.group(3)  # compare by emoji ID
    return False

class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY env var not set.")
        self.ai = OpenAI(api_key=OPENAI_API_KEY)
        self.sent = set()  # (message_id, user_id) cooldown keys

    # -----------------------
    # Manual /translate command
    # -----------------------
    @app_commands.guild_only()
    @app_commands.describe(text="Text to translate", target_lang="Target language code (e.g., en, de, fr)")
    @app_commands.autocomplete(target_lang=lambda it, cur: [
        app_commands.Choice(name=code, value=code)
        for code in SUPPORTED_LANGS if cur.lower() in code][:25]
    )
    @app_commands.command(name="translate", description="Translate a specific text with AI.")
    async def translate(self, interaction: discord.Interaction, text: str, target_lang: str):
        await interaction.response.defer(ephemeral=True)
        target_lang = target_lang.lower()
        if target_lang not in SUPPORTED_LANGS:
            await interaction.followup.send(f"❌ Unsupported language code `{target_lang}`.", ephemeral=True)
            return
        try:
            translated, src, usage = await self.ai_translate(text, target_lang)
            # record stat
            await database.add_translation_stat(interaction.guild_id, interaction.user.id, used_ai=True, tokens_in=usage.get("input",0), tokens_out=usage.get("output",0))
            embed = discord.Embed(description=translated, color=0x00E6F6)
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            timestamp = datetime.utcnow().strftime("%H:%M UTC")
            embed.set_footer(text=f"Translated at {timestamp} • to {target_lang} • detected {src}")
            await interaction.followup.send(embed=embed, ephemeral=False)
        except Exception as e:
            await interaction.followup.send(f"❌ Translation failed: {e}", ephemeral=True)

    # -----------------------
    # Auto react in selected channels
    # -----------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        gid = message.guild.id
        allowed = await database.get_translation_channels(gid)
        if not allowed or message.channel.id not in allowed:
            return

        bot_emote = normalize_emote_input(await database.get_bot_emote(gid) or "🔃")
        try:
            await message.add_reaction(bot_emote)
        except Exception:
            # If custom, try PartialEmoji
            m = CUSTOM_EMOJI_RE.match(bot_emote)
            if m:
                _a, name, eid = m.groups()
                try:
                    await message.add_reaction(discord.PartialEmoji(name=name, id=int(eid), animated=bool(_a)))
                except Exception:
                    print(f"[{gid}] Could not add custom emote {bot_emote} in #{message.channel.id}")
            else:
                print(f"[{gid}] Could not add unicode emote {bot_emote} in #{message.channel.id}")

    # -----------------------
    # React-to-translate
    # -----------------------
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user.bot or not reaction.message.guild:
            return
        msg = reaction.message
        gid = msg.guild.id
        # only on enabled channels
        allowed = await database.get_translation_channels(gid)
        if not allowed or msg.channel.id not in allowed:
            return

        # check emote matches configured
        configured = normalize_emote_input(await database.get_bot_emote(gid) or "🔃")
        reacted = emoji_to_str(reaction.emoji)
        if not same_reaction(configured, reacted):
            return

        key = (msg.id, user.id)
        if key in self.sent:
            return
        self.sent.add(key)
        asyncio.create_task(self._clear(key))

        # target language = user pref or server default or en
        user_lang = (await database.get_user_lang(user.id)) or (await database.get_server_lang(gid)) or "en"
        user_lang = user_lang.lower()
        if user_lang not in SUPPORTED_LANGS:
            user_lang = "en"

        try:
            src_text = msg.content or ""
            translated, src, usage = await self.ai_translate(src_text, user_lang)
            await database.add_translation_stat(gid, user.id, used_ai=True, tokens_in=usage.get("input",0), tokens_out=usage.get("output",0))

            embed = discord.Embed(description=translated, color=0x00E6F6)
            embed.set_author(name=msg.author.display_name, icon_url=msg.author.display_avatar.url)
            ts = msg.created_at.strftime("%H:%M UTC")
            embed.set_footer(text=f"{ts} • to {user_lang} • detected {src}")
            embed.description += f"\n[Original message](https://discord.com/channels/{msg.guild.id}/{msg.channel.id}/{msg.id})"
            await user.send(embed=embed)

            try:
                await reaction.remove(user)
            except Exception:
                pass

        except Exception as e:
            print(f"[{gid}] Translation error: {e}")

    async def _clear(self, key, delay:int=300):
        await asyncio.sleep(delay)
        self.sent.discard(key)

    # -----------------------
    # AI translate helper
    # -----------------------
    async def ai_translate(self, text: str, target_lang: str):
        """
        Uses OpenAI to translate text. Returns (translated_text, detected_lang, usage_dict).
        """
        prompt_system = (
            "You are a concise translator. "
            "Detect the source language and translate the user's text to the requested target language. "
            "Return ONLY the translated text. No notes, no quotes."
        )
        prompt_user = f"Target language: {target_lang}\n\nText:\n{text}"

        # call OpenAI
        resp = self.ai.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": prompt_system},
                {"role": "user", "content": prompt_user}
            ],
            temperature=0,
        )

        out = resp.choices[0].message.content.strip()
        usage = {"input": 0, "output": 0}
        try:
            u = resp.usage
            # map to ints if present
            usage["input"] = int(getattr(u, "prompt_tokens", 0))
            usage["output"] = int(getattr(u, "completion_tokens", 0))
        except Exception:
            pass

        # coarse detection (simple heuristic via model echo is avoided) – fallback 'unknown'
        detected = "unknown"
        return out, detected, usage


async def setup(bot):
    await bot.add_cog(Translate(bot))