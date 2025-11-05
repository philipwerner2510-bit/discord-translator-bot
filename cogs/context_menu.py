# cogs/context_menu.py
import discord
from discord import app_commands
from discord.ext import commands
from utils.brand import COLOR, EMOJI_PRIMARY, footer
from utils import database
from cogs.translate import SUPPORTED_LANGS  # reuse same language list

# Helper to perform translation through the existing Translate cog
async def _do_translation(interaction: discord.Interaction, message: discord.Message, target: str):
    bot = interaction.client
    cog = bot.get_cog("Translate")
    if not cog:
        return await interaction.followup.send("❌ Translator not loaded.", ephemeral=True)

    if not target or target.lower() not in SUPPORTED_LANGS:
        target = "en"

    translated, detected, usage = await cog.ai_translate(message.content or "", target)

    # Record usage
    gid = message.guild.id if message.guild else None
    await database.add_translation_stat(
        gid, interaction.user.id, used_ai=True,
        tokens_in=usage.get("input", 0), tokens_out=usage.get("output", 0)
    )

    embed = discord.Embed(description=translated, color=COLOR)
    embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
    ts = message.created_at.strftime("%H:%M UTC") if message.created_at else "—"
    embed.set_footer(text=f"{EMOJI_PRIMARY} {ts} • to {target} • from {detected} • {footer()}")
    await interaction.followup.send(embed=embed, ephemeral=True)

# Context Menu: Translate → My Language
@app_commands.context_menu(name="Translate → My Language")
async def translate_my_language(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.defer(ephemeral=True)
    gid = message.guild.id if message.guild else None
    target = (await database.get_user_lang(interaction.user.id)) or (await database.get_server_lang(gid)) or "en"
    target = (target or "en").lower()
    await _do_translation(interaction, message, target)

# Context Menu: Translate → Server Default
@app_commands.context_menu(name="Translate → Server Default")
async def translate_server_default(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.defer(ephemeral=True)
    gid = message.guild.id if message.guild else None
    target = (await database.get_server_lang(gid)) or "en"
    target = (target or "en").lower()
    await _do_translation(interaction, message, target)

# Optional Cog shell (keeps loader pattern consistent)
class ContextMenus(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

async def setup(bot: commands.Bot):
    # Add a light Cog (not strictly required, but keeps extension consistent)
    await bot.add_cog(ContextMenus(bot))
    # Register context menus at tree level
    bot.tree.add_command(translate_my_language)
    bot.tree.add_command(translate_server_default)