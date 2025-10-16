import discord
from discord import app_commands
from discord.ext import commands
from utils import database as db

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Set default language for the server
    @app_commands.command(name="defaultlang", description="Set the default translation language for the server")
    @app_commands.checks.has_permissions(administrator=True)
    async def defaultlang(self, interaction: discord.Interaction, lang: str):
        await db.set_guild_default_lang(interaction.guild.id, lang.lower())
        await interaction.response.send_message(f"✅ Server default language set to `{lang}`", ephemeral=True)

    # Multi-channel selection for reaction-based translation
    @app_commands.command(name="channelselection", description="Select multiple channels for translation reactions")
    @app_commands.checks.has_permissions(administrator=True)
    async def channelselection(self, interaction: discord.Interaction):
        channels = [c for c in interaction.guild.text_channels if c.permissions_for(interaction.guild.me).send_messages]

        options = [discord.SelectOption(label=c.name, value=str(c.id)) for c in channels]
        select = discord.ui.Select(
            placeholder="Select channels",
            options=options,
            max_values=len(options)  # allow multiple selection
        )

        async def select_callback(interaction2: discord.Interaction):
            selected_ids = [int(cid) for cid in select.values]
            # Remove all existing channels first
            existing = await db.get_reaction_channels(interaction.guild.id)
            for ch_id in existing:
                await db.remove_reaction_channel(interaction.guild.id, ch_id)
            # Add new channels
            for ch_id in selected_ids:
                await db.add_reaction_channel(interaction.guild.id, ch_id)
            await interaction2.response.send_message(
                f"✅ Reaction channels updated: {', '.join(f'<#{cid}>' for cid in selected_ids)}", ephemeral=True
            )

        select.callback = select_callback
        view = discord.ui.View()
        view.add_item(select)
        await interaction.response.send_message("Select channels for translation reactions:", view=view, ephemeral=True)

    # Set error logging channel
    @app_commands.command(name="seterrorchannel", description="Set a channel for bot error logs")
    @app_commands.checks.has_permissions(administrator=True)
    async def seterrorchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await db.set_guild_error_channel(interaction.guild.id, channel.id)
        await interaction.response.send_message(f"✅ Error logging channel set to {channel.mention}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
