import discord
from discord import app_commands
from discord.ext import commands
from utils import database as db  # make sure you have a database.py handling async db calls

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -----------------------------
    # Set server default language
    # -----------------------------
    @app_commands.command(name="defaultlang", description="Set default server translation language")
    @app_commands.checks.has_permissions(administrator=True)
    async def defaultlang(self, interaction: discord.Interaction, lang: str):
        await interaction.response.defer(ephemeral=True)
        await db.set_server_lang(interaction.guild.id, lang.lower())
        await interaction.followup.send(f"✅ Server default language set to `{lang}`")

    # -----------------------------
    # Set error logging channel
    # -----------------------------
    @app_commands.command(name="seterrorchannel", description="Set channel for error logging")
    @app_commands.checks.has_permissions(administrator=True)
    async def seterrorchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        await db.set_error_channel(interaction.guild.id, channel.id)
        await interaction.followup.send(f"✅ Error logging channel set to {channel.mention}")

    # -----------------------------
    # Channel selection for reaction translations (multi-channel)
    # -----------------------------
    @app_commands.command(name="channelselection", description="Select channels for translation reactions")
    @app_commands.checks.has_permissions(administrator=True)
    async def channelselection(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        channels = [c for c in guild.text_channels if c.permissions_for(guild.me).send_messages]

        if not channels:
            await interaction.followup.send("❌ No channels available where I can send messages.", ephemeral=True)
            return

        # Create select options
        options = [
            discord.SelectOption(label=c.name, value=str(c.id))
            for c in channels
        ]

        # Load current channels from DB for pre-selection (if needed)
        current_channels = await db.get_translation_channels(guild.id)

        select = discord.ui.Select(
            placeholder="Select channels for translation reactions",
            options=options,
            max_values=len(options)
        )

        async def callback(interaction2: discord.Interaction):
            selected_ids = [int(c) for c in select.values]
            await db.set_translation_channels(guild.id, selected_ids)
            await interaction2.response.send_message(f"✅ Translation channels updated!", ephemeral=True)

        select.callback = callback

        view = discord.ui.View()
        view.add_item(select)

        await interaction.followup.send("Select translation channels (multi-select possible):", view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
