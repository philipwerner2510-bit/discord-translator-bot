import discord
from discord import app_commands
from discord.ext import commands
from utils.brand import COLOR, footer
from utils.language_data import codes, label
from utils import database

# helper: call Translate cog
async def _translate_via_cog(interaction: discord.Interaction, message: discord.Message, target: str):
    bot = interaction.client
    cog = bot.get_cog("Translate")
    if not cog:
        e = discord.Embed(description="❌ Translator not loaded.", color=COLOR); e.set_footer(text=footer())
        return await interaction.response.send_message(embed=e, ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    try:
        translated, detected = await cog.ai_translate(message.content or "", target)
        e = discord.Embed(title=f"{label(detected)} → {label(target)}", description=translated, color=COLOR)
        e.set_footer(text=footer()); await interaction.followup.send(embed=e, ephemeral=True)
    except Exception as ex:
        e = discord.Embed(description=f"❌ {ex}", color=COLOR); e.set_footer(text=footer())
        await interaction.followup.send(embed=e, ephemeral=True)

@app_commands.context_menu(name="Translate → My Language")
async def translate_my_language(interaction: discord.Interaction, message: discord.Message):
    lang = (await database.get_user_lang(interaction.user.id)) or (await database.get_server_lang(message.guild.id)) or "en"
    if lang not in codes(): lang = "en"
    await _translate_via_cog(interaction, message, lang)

@app_commands.context_menu(name="Translate → Server Default")
async def translate_server_default(interaction: discord.Interaction, message: discord.Message):
    lang = (await database.get_server_lang(message.guild.id)) or "en"
    if lang not in codes(): lang = "en"
    await _translate_via_cog(interaction, message, lang)

class ContextMenus(commands.Cog):
    def __init__(self, bot): self.bot = bot

async def setup(bot):
    await bot.add_cog(ContextMenus(bot))
    bot.tree.add_command(translate_my_language)
    bot.tree.add_command(translate_server_default)
