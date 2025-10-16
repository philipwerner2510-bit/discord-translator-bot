import discord
from discord.ext import commands
from discord import app_commands
from utils import database

class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setmylang", description="Set your personal translation language")
    async def setmylang(self, interaction: discord.Interaction, lang: str):
        await interaction.response.defer(ephemeral=True)
        try:
            await database.set_user_lang(interaction.user.id, lang.lower())
            await interaction.followup.send(f"✅ Your language has been set to `{lang}`", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error setting your language: {e}", ephemeral=True)

    @app_commands.command(name="translate", description="Translate a message manually")
    async def translate(self, interaction: discord.Interaction, message: str, lang: str = None):
        await interaction.response.defer(ephemeral=True)
        try:
            # Determine target language
            target = lang
            if not target:
                user_lang = await database.get_user_lang(interaction.user.id)
                guild_lang = await database.get_server_lang(interaction.guild.id) if interaction.guild else None
                target = user_lang or guild_lang or "en"

            # Translate using public LibreTranslate
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post("https://libretranslate.de/translate", json={
                    "q": message,
                    "source": "auto",
                    "target": target
                })
                data = resp.json()
                translated_text = data.get("translatedText", "❌ Translation failed")

            embed = discord.Embed(
                description=translated_text,
                color=0xDE002A
            )
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            embed.set_footer(text=f"Translated from auto-detected language → {target}")

            await interaction.followup.send(content=translated_text, embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ Error during translation: {e}", ephemeral=True)

    @app_commands.command(name="help", description="Show bot commands")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        is_admin = interaction.user.guild_permissions.administrator if interaction.guild else False

        embed = discord.Embed(
            title="🤖 Demon Translator Help",
            color=0xDE002A
        )

        # Everyone commands
        embed.add_field(name="/setmylang", value="Set your personal translation language.", inline=False)
        embed.add_field(name="/translate", value="Translate a message manually. Optionally specify language.", inline=False)

        # Admin commands only visible to admins
        if is_admin:
            embed.add_field(name="/defaultlang", value="Set default server translation language.", inline=False)
            embed.add_field(name="/channelselection", value="Select translation channels.", inline=False)
            embed.add_field(name="/seterrorchannel", value="Set channel for error logging.", inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(UserCommands(bot))
