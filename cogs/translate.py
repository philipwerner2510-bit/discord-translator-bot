import os, re, json, asyncio
import discord
from discord.ext import commands
from discord import app_commands
from openai import OpenAI
from utils.brand import COLOR, footer, Z_CONFUSED, Z_SAD
from utils import database
from utils.language_data import SUPPORTED_LANGUAGES, label, codes

AI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CUSTOM_EMOJI_RE = re.compile(r"<(a?):([a-zA-Z0-9_]+):(\d+)>")

def normalize_emote_input(s:str)->str:
    return (s or "").strip()

def reaction_to_str(emoji)->str:
    return str(emoji)

def _same(a:str,b:str)->bool:
    if a==b: return True
    ma, mb = CUSTOM_EMOJI_RE.match(a or ""), CUSTOM_EMOJI_RE.match(b or "")
    if ma and mb: return ma.group(3)==mb.group(3)
    return False

def _lang_list():
    return [l["code"] for l in SUPPORTED_LANGUAGES]

async def ac_lang(interaction, current:str):
    cur = (current or "").lower()
    choices = []
    for l in SUPPORTED_LANGUAGES:
        disp = label(l["code"])
        if cur in l["code"] or cur in l["name"].lower() or cur in disp.lower():
            choices.append(app_commands.Choice(name=disp, value=l["code"]))
        if len(choices)>=25: break
    return choices

class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY not set.")
        self.ai = OpenAI(api_key=OPENAI_API_KEY)
        self.sent = set()

    # /translate (manual)
    @app_commands.guild_only()
    @app_commands.command(name="translate", description="Translate specific text with AI.")
    @app_commands.describe(text="Text to translate", target_lang="Target language (code)")
    @app_commands.autocomplete(target_lang=ac_lang)
    async def translate(self, interaction: discord.Interaction, text: str, target_lang: str):
        await interaction.response.defer(ephemeral=True)

        target_lang = (target_lang or "").lower()
        if target_lang not in _lang_list():
            e = discord.Embed(description=f"{Z_CONFUSED} Unsupported language code `{target_lang}`.", color=COLOR)
            e.set_footer(text=footer()); return await interaction.followup.send(embed=e, ephemeral=True)

        thinking = discord.Embed(description="Translating…", color=COLOR)
        thinking.set_footer(text=footer())
        await interaction.followup.send(embed=thinking, ephemeral=True)

        try:
            translated, detected = await self.ai_translate(text, target_lang)
            # Post result publicly in channel
            embed = discord.Embed(
                title=f"{label(detected)} → {label(target_lang)}",
                description=translated,
                color=COLOR
            )
            embed.set_footer(text=footer())
            await interaction.channel.send(embed=embed)
        except Exception as e:
            err = discord.Embed(description=f"{Z_SAD} Translation failed: `{e}`", color=COLOR)
            err.set_footer(text=footer())
            await interaction.followup.send(embed=err, ephemeral=True)

    # React to translate
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild: return
        gid = message.guild.id
        allowed = await database.get_translation_channels(gid)
        if not allowed or message.channel.id not in allowed: return
        emote = normalize_emote_input(await database.get_bot_emote(gid) or "🔃")
        try:
            await message.add_reaction(emote)
        except Exception:
            m = CUSTOM_EMOJI_RE.match(emote)
            if m:
                _a,name,eid = m.groups()
                try:
                    await message.add_reaction(discord.PartialEmoji(name=name, id=int(eid), animated=bool(_a)))
                except Exception:
                    print(f"[{gid}] Could not add custom emote {emote} in #{message.channel.id}")
            else:
                print(f"[{gid}] Could not add unicode emote {emote} in #{message.channel.id}")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user.bot or not reaction.message.guild: return
        msg = reaction.message
        gid = msg.guild.id
        allowed = await database.get_translation_channels(gid)
        if not allowed or msg.channel.id not in allowed: return

        configured = normalize_emote_input(await database.get_bot_emote(gid) or "🔃")
        reacted = reaction_to_str(reaction.emoji)
        if not _same(configured, reacted): return

        key = (msg.id, user.id)
        if key in self.sent: return
        self.sent.add(key); asyncio.create_task(self._clear(key))

        # user lang or server default
        target = (await database.get_user_lang(user.id)) or (await database.get_server_lang(gid)) or "en"
        if target not in _lang_list(): target="en"

        # DM loading
        loading = discord.Embed(description="Translating…", color=COLOR); loading.set_footer(text=footer())
        try:
            dm_msg = await user.send(embed=loading)
        except Exception:
            return  # can't DM user

        try:
            translated, detected = await self.ai_translate(msg.content or "", target)
            embed = discord.Embed(
                title=f"{label(detected)} → {label(target)}",
                description=translated,
                color=COLOR
            )
            embed.set_footer(text=footer())

            view = discord.ui.View()
            view.add_item(discord.ui.Button(
                label="View Original Message",
                style=discord.ButtonStyle.link,
                url=f"https://discord.com/channels/{msg.guild.id}/{msg.channel.id}/{msg.id}"
            ))

            await dm_msg.edit(embed=embed, view=view)

            # increment presence counter
            self.bot.total_translations = getattr(self.bot, "total_translations", 0) + 1

            try:
                await reaction.remove(user)
            except Exception:
                pass
        except Exception as e:
            err = discord.Embed(description=f"{Z_SAD} Translation failed: `{e}`", color=COLOR)
            err.set_footer(text=footer())
            try:
                await dm_msg.edit(embed=err, view=None)
            except Exception:
                pass

    async def _clear(self, key, delay:int=300):
        await asyncio.sleep(delay); self.sent.discard(key)

    async def ai_translate(self, text:str, target_lang:str):
        # Return only translated text and detected source code
        system = "You are a precise translator. Detect the source language (ISO 639-1) and translate to the requested target."
        user = (
            "Return STRICT JSON: {\"translated\":\"...\",\"detected\":\"xx\"}\n"
            f"Target: {target_lang}\nText:\n{text}"
        )
        resp = self.ai.chat.completions.create(
            model=AI_MODEL,
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            temperature=0,
        )
        raw = resp.choices[0].message.content.strip()
        try:
            data = json.loads(raw)
        except Exception:
            s,e = raw.find("{"), raw.rfind("}")
            data = json.loads(raw[s:e+1]) if s!=-1 and e!=-1 else {"translated": raw, "detected":"unknown"}

        translated = str(data.get("translated","")).strip()
        detected = str(data.get("detected","unknown")).strip().lower()
        if detected not in _lang_list(): detected = "unknown"
        return translated, detected

async def setup(bot):
    await bot.add_cog(Translate(bot))
