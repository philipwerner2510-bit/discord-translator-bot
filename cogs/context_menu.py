import discord
from discord.ext import commands
from discord import app_commands
from utils.brand import COLOR, EMOJI_PRIMARY, footer
from cogs.translate import SUPPORTED_LANGS, Translate
from utils import database

class ContextMenu(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.context_menu(name="Translate → My Language")
    async def translate_my(self, interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer(ephemeral=True)
        cog: Translate = self.bot.get_cog("Translate")
        if not cog:
            return await interaction.followup.send("❌ Translator not loaded.", ephemeral=True)
        gid = message.guild.id if message.guild else None
        target = (await database.get_user_lang(interaction.user.id)) or (await database.get_server_lang(gid)) or "en"
        target = target.lower() if target else "en"
        if target not in SUPPORTED_LANGS:
            target = "en"

        try:
            translated, detected, usage = await cog.ai_translate(message.content or "", target)
            await database.add_translation_stat(
                gid, interaction.user.id, used_ai=True,
                tokens_in=usage.get("input",0), tokens_out=usage.get("output",0)
            )
            embed = discord.Embed(description=translated, color=COLOR)
            embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
            ts = message.created_at.strftime("%H:%M UTC") if message.created_at else "—"
            embed.set_footer(text=f"{EMOJI_PRIMARY} {ts} • to {target} • from {detected} • {footer()}")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed: {e}", ephemeral=True)

    @app_commands.context_menu(name="Translate → Server Default")
    async def translate_server(self, interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer(ephemeral=True)
        cog: Translate = self.bot.get_cog("Translate")
        if not cog:
            return await interaction.followup.send("❌ Translator not loaded.", ephemeral=True)
        gid = message.guild.id if message.guild else None
        target = (await database.get_server_lang(gid)) or "en"
        target = target.lower()
        if target not in SUPPORTED_LANGS:
            target = "en"

        try:
            translated, detected, usage = await cog.ai_translate(message.content or "", target)
            await database.add_translation_stat(
                gid, interaction.user.id, used_ai=True,
                tokens_in=usage.get("input",0), tokens_out=usage.get("output",0)
            )
            embed = discord.Embed(description=translated, color=COLOR)
            embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
            ts = message.created_at.strftime("%H:%M UTC") if message.created_at else "—"
            embed.set_footer(text=f"{EMOJI_PRIMARY} {ts} • to {target} • from {detected} • {footer()}")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed: {e}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ContextMenu(bot))