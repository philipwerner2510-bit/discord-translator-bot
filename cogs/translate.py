import discord
from discord.ext import commands
import asyncio
from googletrans import Translator
from utils.cache import TranslationCache
from utils import database
from utils.logging_utils import log_error
import os
import time
from datetime import datetime

BOT_COLOR = 0xde002a
translator = Translator()
cache = TranslationCache(ttl=600)

AI_COST_CAP = 10.0
AI_APPROACH_LIMIT = 8.0

import openai
openai.api_key = os.getenv("OPENAI_API_KEY")


# GPT-4o Mini translate
async def ai_translate(text, target_lang):
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You translate text to {target_lang}. Only translate, never explain."},
                {"role": "user", "content": text}
            ],
            temperature=0.2
        )
        ai_text = response["choices"][0]["message"]["content"]
        tokens = response["usage"]["total_tokens"]
        cost = tokens * 0.000003
        await database.add_ai_usage(tokens, cost)
        return ai_text, tokens, cost
    except Exception:
        return None, 0, 0.0


async def google_translate(text, target_lang):
    try:
        result = translator.translate(text, dest=target_lang)
        return result.text
    except Exception:
        return None


class Translate(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.reacted_messages = set()

    # ------------------------------------
    # Reaction trigger
    # ------------------------------------
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        message = reaction.message

        gid = getattr(message.guild, "id", None)
        if not gid:
            return

        allowed = await database.get_translation_channels(gid)
        if message.channel.id not in allowed:
            return

        key = (message.id, user.id)
        if key in self.reacted_messages:
            return
        self.reacted_messages.add(key)

        try:
            await self.handle_reaction(reaction, user)
        finally:
            await asyncio.sleep(2)
            self.reacted_messages.discard(key)

    # ------------------------------------
    async def handle_reaction(self, reaction, user):
        language = await database.get_user_lang(user.id)
        if not language:
            await self.prompt_language_choice(reaction.message, user)
            return

        await self.translate_message(reaction.message, user, language)

    # ------------------------------------
    # Prompt user to set a language
    # ------------------------------------
    async def prompt_language_choice(self, msg, user):
        try:
            dropdown = discord.ui.Select(
                placeholder="Choose your language 🌍",
                options=[
                    discord.SelectOption(label="English", value="en", emoji="🇬🇧"),
                    discord.SelectOption(label="German", value="de", emoji="🇩🇪"),
                    discord.SelectOption(label="Spanish", value="es", emoji="🇪🇸"),
                    discord.SelectOption(label="French", value="fr", emoji="🇫🇷"),
                    discord.SelectOption(label="Italian", value="it", emoji="🇮🇹"),
                    discord.SelectOption(label="Japanese", value="ja", emoji="🇯🇵"),
                    discord.SelectOption(label="Korean", value="ko", emoji="🇰🇷"),
                    discord.SelectOption(label="Chinese", value="zh", emoji="🇨🇳"),
                ]
            )

            view = discord.ui.View()
            view.add_item(dropdown)

            async def callback(interaction: discord.Interaction):
                await database.set_user_lang(user.id, dropdown.values[0])
                await interaction.response.send_message(
                    f"✅ Your language has been set to `{dropdown.values[0]}`!",
                    ephemeral=True
                )
                await self.translate_message(msg, user, dropdown.values[0])

            dropdown.callback = callback

            await user.send("🌍 Please select your translation language:", view=view)

        except Exception as e:
            gid = msg.guild.id if msg.guild else 0
            await log_error(self.bot, gid, "Prompt send failed", e, admin_notify=True)

    # ------------------------------------
    async def translate_message(self, msg, user, target_lang):
        try:
            original = msg.content
            if not original.strip():
                return

            cached = await cache.get(original, target_lang)
            if cached:
                translation = cached
            else:
                ai_enabled = await database.get_ai_enabled(msg.guild.id)
                tokens, cost = 0, 0.0
                translation = None

                if ai_enabled:
                    tokens_before, cost_before = await database.get_current_ai_usage()
                    translation, tokens, cost = await ai_translate(original, target_lang)
                    tokens_after, cost_after = await database.get_current_ai_usage()

                    current_cost = cost_after
                    if current_cost >= AI_COST_CAP:
                        ai_enabled = False
                        await database.set_ai_enabled(msg.guild.id, False)

                    elif current_cost >= AI_APPROACH_LIMIT:
                        channel = await database.get_error_channel(msg.guild.id)
                        if channel:
                            ch = msg.guild.get_channel(channel)
                            if ch:
                                await ch.send(
                                    f"⚠️ AI usage at **€{current_cost:.2f}/€10**.\n"
                                    f"Bot will fallback to Google soon!"
                                )

                if not translation:
                    translation = await google_translate(original, target_lang)

                if not translation:
                    return

                await cache.set(original, target_lang, translation)

            try:
                await msg.remove_reaction(reaction=self.get_reaction(msg), member=self.bot.user)
            except:
                pass

            await msg.reply(
                f"🌍 **Translated to `{target_lang}`:**\n> {translation}",
                mention_author=False
            )

            self.bot.total_translations += 1

        except Exception as e:
            gid = msg.guild.id
            await log_error(self.bot, gid, "Reaction handler error", e, admin_notify=True)

    def get_reaction(self, msg):
        for e in msg.reactions:
            if e.me:
                return e
        return None


async def setup(bot):
    await bot.add_cog(Translate(bot))