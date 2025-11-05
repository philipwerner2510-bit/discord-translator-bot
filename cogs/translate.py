import re
import asyncio
import json
from datetime import datetime
import os
import discord
from discord.ext import commands
from discord import app_commands
from openai import OpenAI
from utils import database
from utils.brand import COLOR, EMOJI_THINKING, EMOJI_PRIMARY, footer

AI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

SUPPORTED_LANGS = [
    "en","zh","hi","es","fr","ar","bn","pt","ru","ja",
    "de","jv","ko","vi","mr","ta","ur","tr","it","th",
    "gu","kn","ml","pa","or","fa","sw","am","ha","yo"
]

CUSTOM_EMOJI_RE = re.compile(r"<(a?):([a-zA-Z0-9_]+):(\d+)>")

def normalize_emote_input(s: str) -> str:
    return (s or "").strip()

def emoji_to_str(emoji) -> str:
    return str(emoji)

def same_reaction(a: str, b: str) -> bool:
    if a == b:
        return True
    ma, mb = CUSTOM_EMOJI_RE.match(a or ""), CUSTOM_EMOJI_RE.match(b or "")
    if ma and mb:
        return ma.group(3) == mb.group(3)
    return False

async def ac_lang(interaction: discord.Interaction, current: str):
    current = (current or "").lower()
    items = [code for code in SUPPORTED_LANGS if current in code]
    return [app_commands.Choice(name=code, value=code) for code in items[:25]]

class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY env var not set.")
        self.ai = OpenAI(api_key=OPENAI_API_KEY)
        self.sent = set()

    @app_commands.guild_only()
    @app_commands.describe(text="Text to translate", target_lang="Target language code (e.g., en, de, fr)")
    @app_commands.autocomplete(target_lang=ac_lang)
    @app_commands.command(name="translate", description="Translate a specific text with AI.")
    async def translate(self, interaction: discord.Interaction, text: str, target_lang: str):
        await interaction.response.defer(ephemeral=True)

        target_lang = (target_lang or "").lower()
        if target_lang not in SUPPORTED_LANGS:
            return await interaction.followup.send(f"❌ Unsupported language code `{target_lang}`.", ephemeral=True)

        thinking = discord.Embed(description=f"{EMOJI_THINKING} Translating…", color=COLOR)
        thinking.set_footer(text=footer())
        await interaction.followup.send(embed=thinking, ephemeral=True)

        try:
            translated, detected, usage = await self.ai_translate(text, target_lang)
            await database.add_translation_stat(
                interaction.guild_id, interaction.user.id, used_ai=True,
                tokens_in=usage.get("input",0), tokens_out=usage.get("output",0)
            )
            embed = discord.Embed(description=translated, color=COLOR)
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            ts = datetime.utcnow().strftime("%H:%M UTC")
            embed.set_footer(text=f"{EMOJI_PRIMARY} {ts} • to {target_lang} • from {detected} • {footer()}")
            await interaction.channel.send(embed=embed)

            done = discord.Embed(description="✅ Sent translation.", color=COLOR)
            done.set_footer(text=footer())
            await interaction.followup.send(embed=done, ephemeral=True)
        except Exception as e:
            err = discord.Embed(description=f"❌ Translation failed: `{e}`", color=COLOR)
            err.set_footer(text=footer())
            await interaction.followup.send(embed=err, ephemeral=True)

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
            m = CUSTOM_EMOJI_RE.match(bot_emote)
            if m:
                _a, name, eid = m.groups()
                try:
                    await message.add_reaction(discord.PartialEmoji(name=name, id=int(eid), animated=bool(_a)))
                except Exception:
                    print(f"[{gid}] Could not add custom emote {bot_emote} in #{message.channel.id}")
            else:
                print(f"[{gid}] Could not add unicode emote {bot_emote} in #{message.channel.id}")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user.bot or not reaction.message.guild:
            return
        msg = reaction.message
        gid = msg.guild.id
        allowed = await database.get_translation_channels(gid)
        if not allowed or msg.channel.id not in allowed:
            return

        configured = normalize_emote_input(await database.get_bot_emote(gid) or "🔃")
        reacted = emoji_to_str(reaction.emoji)
        if not same_reaction(configured, reacted):
            return

        key = (msg.id, user.id)
        if key in self.sent:
            return
        self.sent.add(key)
        asyncio.create_task(self._clear(key))

        user_lang = (await database.get_user_lang(user.id)) or (await database.get_server_lang(gid)) or "en"
        user_lang = user_lang.lower()
        if user_lang not in SUPPORTED_LANGS:
            user_lang = "en"

        try:
            thinking = discord.Embed(description=f"{EMOJI_THINKING} Translating…", color=COLOR)
            thinking.set_footer(text=footer())
            dm_msg = await user.send(embed=thinking)

            src_text = msg.content or ""
            translated, detected, usage = await self.ai_translate(src_text, user_lang)
            await database.add_translation_stat(
                gid, user.id, used_ai=True,
                tokens_in=usage.get("input",0), tokens_out=usage.get("output",0)
            )

            embed = discord.Embed(description=translated, color=COLOR)
            embed.set_author(name=msg.author.display_name, icon_url=msg.author.display_avatar.url)
            ts = msg.created_at.strftime("%H:%M UTC")
            embed.set_footer(text=f"{EMOJI_PRIMARY} {ts} • to {user_lang} • from {detected} • {footer()}")
            embed.description += f"\n[Original message](https://discord.com/channels/{msg.guild.id}/{msg.channel.id}/{msg.id})"

            await dm_msg.edit(embed=embed)

            try:
                await reaction.remove(user)
            except Exception:
                pass
        except Exception as e:
            print(f"[{gid}] Translation error: {e}")

    async def _clear(self, key, delay:int=300):
        await asyncio.sleep(delay)
        self.sent.discard(key)

    async def ai_translate(self, text: str, target_lang: str):
        system = (
            "You are a precise translator. "
            "Detect the source language (ISO 639-1 code) and translate the user's text to the requested target language."
        )
        user = (
            "Return ONLY strict JSON with keys: translated, detected.\n"
            "• detected must be the ISO 639-1 code of the source language (e.g., 'en','de','es').\n"
            "• translated must contain ONLY the translated text (no notes).\n\n"
            f"Target language: {target_lang}\n"
            f"Text:\n{text}"
        )

        resp = self.ai.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user}
            ],
            temperature=0,
        )

        raw = resp.choices[0].message.content.strip()
        usage = {"input": 0, "output": 0}
        try:
            u = resp.usage
            usage["input"] = int(getattr(u, "prompt_tokens", 0))
            usage["output"] = int(getattr(u, "completion_tokens", 0))
        except Exception:
            pass

        parsed = None
        try:
            parsed = json.loads(raw)
        except Exception:
            start = raw.find("{"); end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                try: parsed = json.loads(raw[start:end+1])
                except Exception: parsed = None

        if isinstance(parsed, dict):
            translated = str(parsed.get("translated", "")).strip()
            detected = str(parsed.get("detected", "unknown")).strip().lower()
            if not detected or len(detected) > 5:
                detected = "unknown"
            return translated, detected, usage

        return raw, "unknown", usage

async def setup(bot):
    await bot.add_cog(Translate(bot))