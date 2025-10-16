import discord
from discord import app_commands
from discord.ext import commands
from utils import database as db

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="defaultlang", description="Set default server translation language")
    @app_commands.checks.has_permissions(administrator=True)
    async def defaultlang(self, interaction: discord.Interaction, lang: str):
        await interaction.response.defer(ephemeral=True)
        await db.set_server_lang(interaction.guild.id, lang.lower())
        await interaction.followup.send(f"✅ Server default language set to `{lang}`")

    @app_commands.command(name="seterrorchannel", description="Set error logging channel")
    @app_commands.checks.has_permissions(administrator=True)
    async def seterrorchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        await db.set_error_channel(interaction.guild.id, channel.id)
        await interaction.followup.send(f"✅ Error logging channel set to {channel.mention}")

    @app_commands.command(name="channelselection", description="Select channels for reaction translations")
    @app_commands.checks.has_permissions(administrator=True)
    async def channelselection(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        channels = [c for c in guild.text_channels if c.permissions_for(guild.me).send_messages]
        options = [
            discord.SelectOption(label=c.name, value=str(c.id))
            for c in channels
        ]
        select = discord.ui.Select(placeholder="Select translation channels", options=options, max_values=len(options))
        
        async def callback(interaction2: discord.Interaction):
            selected = [int(cid) for cid in select.values]
            await db.set_translation_channels(guild.id, selected)
            await interaction2.response.send_message(f"✅ Translation channels updated!", ephemeral=True)
        
        select.callback = callback
        view = discord.ui.View()
        view.add_item(select)
        await interaction.followup.send("Select translation channels:", view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
