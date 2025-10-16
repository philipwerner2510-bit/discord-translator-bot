import discord
from discord.ext import commands
from discord import app_commands
from utils import database

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="defaultlang", description="Set server default translation language")
    @app_commands.checks.has_permissions(administrator=True)
    async def defaultlang(self, interaction: discord.Interaction, lang: str):
        await interaction.response.defer(ephemeral=True)
        try:
            await database.set_server_lang(interaction.guild.id, lang.lower())
            await interaction.followup.send(f"✅ Server default language set to `{lang}`", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @app_commands.command(name="channelselection", description="Select channels for translation reactions")
    @app_commands.checks.has_permissions(administrator=True)
    async def channelselection(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        channels = [c for c in guild.text_channels if c.permissions_for(guild.me).send_messages]

        if not channels:
            await interaction.followup.send("❌ No channels available to select.", ephemeral=True)
            return

        options = [
            discord.SelectOption(label=c.name, value=str(c.id))
            for c in channels[:25]
        ]

        select = discord.ui.Select(
            placeholder="Select translation channels",
            options=options,
            min_values=1,
            max_values=len(options)
        )

        async def callback(interact: discord.Interaction):
            selected_channels = [int(x) for x in select.values]
            await database.set_translation_channels(guild.id, selected_channels)
            await interact.response.send_message(
                f"✅ Translation channels set: {', '.join(f'<#{x}>' for x in selected_channels)}",
                ephemeral=True
            )

        select.callback = callback
        view = discord.ui.View(timeout=180)
        view.add_item(select)
        await interaction.followup.send("Select translation channels:", view=view, ephemeral=True)

    @app_commands.command(name="seterrorchannel", description="Set channel for error logging")
    @app_commands.checks.has_permissions(administrator=True)
    async def seterrorchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        try:
            await database.set_error_channel(interaction.guild.id, channel.id)
            await interaction.followup.send(f"✅ Error channel set to {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @defaultlang.error
    @channelselection.error
    @seterrorchannel.error
    async def admin_error(self, interaction, error):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message("🚫 You need Administrator permissions.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
