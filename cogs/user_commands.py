import os
import discord
from discord.ext import commands
from discord import app_commands

BOT_COLOR = 0xDE002A
OWNER_ID = 762267166031609858  # Polarix1954

def build_invite_url(app_id: int) -> str:
    perms = 274878188544
    return f"https://discord.com/oauth2/authorize?client_id={app_id}&permissions={perms}&scope=bot%20applications.commands"

# Lazy OpenAI client helper (same pattern as translate.py)
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


class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="How to use Demon Translator.")
    async def help_cmd(self, interaction: discord.Interaction):
        app_id = self.bot.user.id if self.bot.user else 0
        invite_url = build_invite_url(app_id)

        embed = discord.Embed(
            title="📖 Demon Translator — Quick Help",
            color=BOT_COLOR,
            description=(
                "Use me to translate messages **instantly**:\n\n"
                "1) **React** to any message with the bot's emote to translate it.\n"
                "2) Choose your language via **/setmylang** (dropdown UI).\n"
                "3) Use **/translate** to translate any custom text.\n\n"
                "I use **LibreTranslate** for normal texts (fast & free) and **AI (GPT-4o mini)** "
                "for slang, long, or complex messages — so results feel natural 😈"
            )
        )
        embed.add_field(
            name="Useful Commands",
            value=(
                "• `/setmylang` — pick your personal language (dropdown)\n"
                "• `/translate <text>` — manual translation (AI quality)\n"
                "• `/ping` — check if I'm alive\n"
                "• Admins: `/aisettings`, `/settings`, `/channelselection`, `/defaultlang`, `/librestatus`\n"
            ),
            inline=False
        )
        embed.add_field(
            name="Tips",
            value=(
                "• If you don't receive a DM, I’ll reply in the channel.\n"
                "• Admins can set an error channel with `/seterrorchannel` to get AI budget warnings.\n"
                "• I cache translations for 24h to save tokens & speed things up."
            ),
            inline=False
        )
        embed.set_footer(text="Demon Translator © by Polarix1954 😈🔥")

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="➕ Invite Me", url=invite_url, style=discord.ButtonStyle.link))

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="ping", description="Check bot latency.")
    async def ping_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"🏓 Pong! {round(self.bot.latency * 1000)}ms", ephemeral=True)

    @app_commands.command(name="aitest", description="Owner-only: Run a quick AI translation demo.")
    async def aitest_cmd(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            return await interaction.response.send_message("❌ Owner only.", ephemeral=True)

        client = get_oai_client()
        if not client:
            return await interaction.response.send_message("⚠️ No OPENAI_API_KEY set.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        sample = "Nah bro that’s cap, ain’t no way he pulled that W 💀🔥"
        target_lang = "de"

        try:
            resp = await interaction.client.loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system",
                         "content": f"Translate the user's message to '{target_lang}'. "
                                    f"Preserve tone, slang and emojis. Return only the translation."},
                        {"role": "user", "content": sample},
                    ],
                    temperature=0.2,
                )
            )
            out = resp.choices[0].message.content.strip()

            embed = discord.Embed(
                title="🧪 AI Translation Demo",
                color=BOT_COLOR,
                description=f"**Source:** `{sample}`\n**→ {target_lang.upper()}:** {out}"
            )
            embed.set_footer(text="Engine: GPT-4o mini")
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ AI demo failed: `{e}`", ephemeral=True)


async def setup(bot):
    await bot.add_cog(UserCommands(bot))