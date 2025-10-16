import discord
from discord.ext import commands
from discord import app_commands
from utils import database

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="defaultlang", description="Set default language for this server")
    @app_commands.checks.has_permissions(administrator=True)
    async def defaultlang(self, interaction: discord.Interaction, lang: str):
        await interaction.response.defer(ephemeral=True)
        await database.set_server_lang(interaction.guild.id, lang.lower())
        await interaction.followup.send(f"✅ Default language set to `{lang}`", ephemeral=True)

    @app_commands.command(name="channelselection", description="Select channels for auto-translate")
    @app_commands.checks.has_permissions(administrator=True)
    async def channelselection(self, interaction: discord.Interaction):
        channels = interaction.guild.text_channels
        options = [discord.SelectOption(label=c.name, value=str(c.id)) for c in channels[:25]]

        select = discord.ui.Select(
            placeholder="Select channels...",
            min_values=1,
            max_values=len(options),
            options=options
        )

        async def callback(i: discord.Interaction):
            channel_ids = [int(x) for x in select.values]
            await database.set_translation_channels(interaction.guild.id, channel_ids)
            await i.response.send_message(
                f"✅ Channels set: {', '.join(f'<#{cid}>' for cid in channel_ids)}",
                ephemeral=True
            )

        select.callback = callback
        view = discord.ui.View(timeout=60)
        view.add_item(select)
        await interaction.response.send_message("Select translation channels:", view=view, ephemeral=True)

    @app_commands.command(name="seterrorchannel", description="Set error logging channel")
    @app_commands.checks.has_permissions(administrator=True)
    async def seterrorchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await database.set_error_channel(interaction.guild.id, channel.id)
        await interaction.response.send_message(f"✅ Error channel set to {channel.mention}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
