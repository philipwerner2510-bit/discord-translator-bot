import os
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
from utils import database

BOT_COLOR = 0xDE002A
SUPPORTED_LANGS = ["en","de","es","fr","it","ja","ko","zh"]

def is_admin():
    def predicate(interaction: discord.Interaction):
        return interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)

def libre_endpoint() -> str:
    return os.getenv("LIBRE_URL", "https://libretranslate.de/translate")

def libre_base() -> str:
    url = libre_endpoint().rstrip("/")
    if url.endswith("/translate"):
        return url[: -len("/translate")]
    return url

# Lazy OpenAI client helper
from openai import OpenAI
_oai_client = None
def get_oai_client():
    global _oai_client
    if _oai_client is None:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            return None
        try:
            _oai_client = OpenAI(api_key=key)
        except Exception:
            _oai_client = None
    return _oai_client


class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @is_admin()
    @app_commands.command(name="defaultlang", description="Set the default translation language for this server.")
    async def defaultlang(self, interaction: discord.Interaction, lang: str):
        await interaction.response.defer(ephemeral=True)
        lang = lang.lower()
        if lang not in SUPPORTED_LANGS:
            return await interaction.followup.send(
                f"❌ Invalid language. Supported: {', '.join(SUPPORTED_LANGS)}",
                ephemeral=True
            )
        await database.set_server_lang(interaction.guild.id, lang)
        await interaction.followup.send(f"✅ Default server language set to `{lang}`.", ephemeral=True)

    @is_admin()
    @app_commands.command(name="channelselection", description="Choose channels where translations are active.")
    async def channelselection(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        options = [
            discord.SelectOption(label=ch.name, value=str(ch.id))
            for ch in guild.text_channels
        ]
        if not options:
            return await interaction.followup.send("No text channels found.", ephemeral=True)

        select = discord.ui.Select(
            placeholder="Select translation channels…",
            min_values=1,
            max_values=min(25, len(options)),
            options=options
        )

        async def cb(inter: discord.Interaction):
            ids = list(map(int, select.values))
            await database.set_translation_channels(guild.id, ids)
            txt = ", ".join(f"<#{i}>" for i in ids)
            await inter.response.send_message(f"✅ Translation enabled in: {txt}", ephemeral=True)

        view = discord.ui.View(timeout=120)
        select.callback = cb
        view.add_item(select)

        await interaction.followup.send(
            "Select the channels where the bot should react for translation:",
            view=view,
            ephemeral=True
        )

    @is_admin()
    @app_commands.command(name="seterrorchannel", description="Set a channel where AI warnings & errors appear.")
    async def seterrorchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await database.set_error_channel(interaction.guild.id, channel.id)
        await interaction.response.send_message(f"✅ Error channel set to {channel.mention}", ephemeral=True)

    @is_admin()
    @app_commands.command(name="emote", description="Set the bot's reaction emote for translation triggers.")
    async def emote(self, interaction: discord.Interaction, emote: str):
        await database.set_bot_emote(interaction.guild.id, emote.strip())
        await interaction.response.send_message(f"✅ Reaction emote set to {emote}", ephemeral=True)

    @is_admin()
    @app_commands.command(name="aisettings", description="Enable or disable AI translations for this server.")
    async def aisettings(self, interaction: discord.Interaction, enabled: bool):
        await interaction.response.defer(ephemeral=True)
        await database.set_ai_enabled(interaction.guild.id, enabled)
        status = "🧠 AI Enabled ✅" if enabled else "⚙️ AI Disabled — Libre-only"
        await interaction.followup.send(status, ephemeral=True)

    @is_admin()
    @app_commands.command(name="settings", description="View translation settings for this server.")
    async def settings(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        gid = interaction.guild.id

        default_lang = await database.get_server_lang(gid) or "Not set"
        err_channel_id = await database.get_error_channel(gid)
        emote = await database.get_bot_emote(gid) or "🔁"
        channels = await database.get_translation_channels(gid)
        ai_enabled = await database.get_ai_enabled(gid)

        libre_url = libre_endpoint()
        cache_info = "✅ Enabled (24h TTL)"

        ch_list = ", ".join(f"<#{c}>" for c in channels) if channels else "None"
        err_ch = f"<#{err_channel_id}>" if err_channel_id else "Not set"
        ai_status = "🧠 Enabled" if ai_enabled else "⚙️ Disabled"

        embed = discord.Embed(title="🛠️ Server Settings", color=BOT_COLOR)
        embed.add_field(name="Default Language", value=str(default_lang), inline=True)
        embed.add_field(name="AI Mode", value=ai_status, inline=True)
        embed.add_field(name="Reaction Emote", value=emote, inline=True)
        embed.add_field(name="Error Channel", value=err_ch, inline=True)
        embed.add_field(name="Translation Channels", value=ch_list, inline=False)
        embed.add_field(name="Libre Endpoint", value=f"`{libre_url}`", inline=False)
        embed.add_field(name="Cache", value=cache_info, inline=True)

        # Buttons: Test AI + Ping Libre
        view = discord.ui.View(timeout=120)

        test_btn = discord.ui.Button(label="🧪 Test AI Now", style=discord.ButtonStyle.primary)
        async def test_cb(btn_inter: discord.Interaction):
            if not btn_inter.user.guild_permissions.administrator:
                return await btn_inter.response.send_message("❌ Admins only.", ephemeral=True)
            if not ai_enabled:
                return await btn_inter.response.send_message(
                    "⚙️ AI is **disabled**. Enable it with `/aisettings true`.",
                    ephemeral=True
                )

            client = get_oai_client()
            if not client:
                return await btn_inter.response.send_message(
                    "⚠️ No `OPENAI_API_KEY` set. Cannot run AI test.",
                    ephemeral=True
                )

            try:
                target = default_lang if default_lang in SUPPORTED_LANGS else "en"
                sample = "This is a quick AI self-check. If you see this translated, AI is working."
                resp = await btn_inter.client.loop.run_in_executor(
                    None,
                    lambda: client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system",
                             "content": f"Translate the user's message to '{target}'. Return only the translation."},
                            {"role": "user", "content": sample},
                        ],
                        temperature=0.2,
                    )
                )
                out = resp.choices[0].message.content.strip()
                await btn_inter.response.send_message(
                    f"✅ **AI OK** — `{target}`:\n> {out}",
                    ephemeral=True
                )
            except Exception as e:
                await btn_inter.response.send_message(f"❌ AI test failed: `{e}`", ephemeral=True)

        test_btn.callback = test_cb
        view.add_item(test_btn)

        ping_btn = discord.ui.Button(label="🔌 Ping Libre", style=discord.ButtonStyle.secondary)
        async def ping_cb(btn_inter: discord.Interaction):
            if not btn_inter.user.guild_permissions.administrator:
                return await btn_inter.response.send_message("❌ Admins only.", ephemeral=True)

            base = libre_base()
            url = f"{base}/languages"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=8) as r:
                        if r.status != 200:
                            return await btn_inter.response.send_message(
                                f"⚠️ Libre responded with HTTP {r.status}. Endpoint: `{url}`",
                                ephemeral=True
                            )
                        data = await r.json()
                        langs = [f"`{x.get('code','?')}` {x.get('name','?')}" for x in data][:24]
                        body = "\n".join(langs) if langs else "No languages reported."
                        await btn_inter.response.send_message(
                            f"✅ **Libre OK** — {len(data)} languages\n{body}",
                            ephemeral=True
                        )
            except Exception as e:
                await btn_inter.response.send_message(
                    f"❌ Libre ping failed for `{url}`:\n`{e}`",
                    ephemeral=True
                )

        ping_btn.callback = ping_cb
        view.add_item(ping_btn)

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @is_admin()
    @app_commands.command(name="librestatus", description="Ping the configured Libre endpoint and list languages.")
    async def librestatus(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        base = libre_base()
        url = f"{base}/languages"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=8) as r:
                    if r.status != 200:
                        return await interaction.followup.send(
                            f"⚠️ Libre responded with HTTP {r.status}. Endpoint: `{url}`",
                            ephemeral=True
                        )
                    data = await r.json()
                    langs = [f"`{x.get('code','?')}` {x.get('name','?')}" for x in data][:50]
                    body = "\n".join(langs) if langs else "No languages reported."
                    await interaction.followup.send(
                        f"✅ **Libre OK** — {len(data)} languages\n{body}",
                        ephemeral=True
                    )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Libre ping failed for `{url}`:\n`{e}`",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))