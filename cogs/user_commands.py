import discord
from discord.ext import commands
from discord import app_commands
from utils import database

BOT_COLOR = 0xde002a
OWNER_ID = 762267166031609858

SUPPORTED_LANGS = ["en","de","es","fr","it","ja","ko","zh"]


class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ✅ Set My Language (UI)
    @app_commands.command(name="setmylang", description="Choose your personal translation language.")
    async def setmylang(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        options = [
            discord.SelectOption(label="English", value="en", emoji="🇬🇧"),
            discord.SelectOption(label="German", value="de", emoji="🇩🇪"),
            discord.SelectOption(label="Spanish", value="es", emoji="🇪🇸"),
            discord.SelectOption(label="French", value="fr", emoji="🇫🇷"),
            discord.SelectOption(label="Italian", value="it", emoji="🇮🇹"),
            discord.SelectOption(label="Japanese", value="ja", emoji="🇯🇵"),
            discord.SelectOption(label="Korean", value="ko", emoji="🇰🇷"),
            discord.SelectOption(label="Chinese", value="zh", emoji="🇨🇳"),
        ]

        select = discord.ui.Select(
            placeholder="Select your language 🌍",
            options=options
        )
        view = discord.ui.View()
        view.add_item(select)

        async def cb(inter):
            lang = select.values[0]
            await database.set_user_lang(inter.user.id, lang)
            await inter.response.send_message(
                f"✅ Language updated to `{lang}`!",
                ephemeral=True
            )

        select.callback = cb
        await interaction.followup.send("🌍 Pick your language:", view=view, ephemeral=True)

    # ✅ Public Info & Help
    @app_commands.command(name="help", description="Show user guide.")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 Demon Translator Help",
            description="How to use me:",
            color=BOT_COLOR
        )
        embed.add_field(
            name="✅ Step 1",
            value="Use `/setmylang` to select your language.",
            inline=False
        )
        embed.add_field(
            name="✅ Step 2",
            value="React with the bot's emote to translate messages!",
            inline=False
        )
        embed.add_field(
            name="💡 Admin Controls",
            value="Admins can use `/aisettings`, `/settings`, `/channelselection`, `/defaultlang`",
            inline=False
        )
        embed.set_footer(text="Bot created by Polarix1954 😈🔥")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ✅ Quick connection test
    @app_commands.command(name="ping", description="Check bot response time.")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"🏓 Pong! {round(self.bot.latency * 1000)}ms", ephemeral=True)

    # ✅ Owner-only AI test command
    @app_commands.command(name="aitest", description="Test AI translation (Owner Only)")
    async def aitest(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            return await interaction.response.send_message("❌ Owner only.", ephemeral=True)

        example_text = "Nah bro that’s cap, ain’t no way he pulled that W 💀🔥"
        target = "de"

        embed = discord.Embed(
            title="🧪 AI Translation Test",
            description=f"Translating: `{example_text}`",
            color=BOT_COLOR
        )
        embed.set_footer(text="Demon Translator AI — GPT-4o Mini Mode")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(UserCommands(bot))