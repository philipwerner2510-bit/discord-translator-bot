import discord
from discord.ext import commands
from discord import app_commands
from utils import database

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -----------------------
    # Set server default language
    # -----------------------
    @app_commands.command(name="defaultlang", description="Set default translation language for the server.")
    async def defaultlang(self, interaction: discord.Interaction, lang: str):
        try:
            await database.set_server_lang(interaction.guild.id, lang.lower())
            await interaction.response.send_message(f"✅ Server default language set to `{lang}`", ephemeral=True)
        except Exception as e:
            await self.admin_error(interaction, e)

    # -----------------------
    # Multi-select channel selection
    # -----------------------
    @app_commands.command(name="channelselection", description="Select channels where the bot reacts for translations.")
    async def channelselection(self, interaction: discord.Interaction):
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
                return

            options = [
                discord.SelectOption(label=ch.name, value=str(ch.id))
                for ch in guild.text_channels
            ]

            if not options:
                await interaction.response.send_message("❌ No text channels found.", ephemeral=True)
                return

            # Create dropdown
            select = discord.ui.Select(
                placeholder="Select channels for translation reactions...",
                options=options,
                min_values=1,
                max_values=len(options)
            )

            async def select_callback(select_interaction: discord.Interaction):
                selected_ids = [int(val) for val in select.values]
                await database.set_translation_channels(guild.id, selected_ids)
                await select_interaction.response.send_message(
                    f"✅ Channels updated: {', '.join([guild.get_channel(ch_id).mention for ch_id in selected_ids])}",
                    ephemeral=True
                )

            select.callback = select_callback
            view = discord.ui.View()
            view.add_item(select)

            await interaction.response.send_message(
                "Select one or multiple channels for translation reactions:",
                view=view,
                ephemeral=True
            )

        except Exception as e:
            await self.admin_error(interaction, e)

    # -----------------------
    # Error handler for admin commands
    # -----------------------
    async def admin_error(self, interaction: discord.Interaction, error):
        try:
            # If already acknowledged, use followup
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ Error: {error}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)
        except Exception as e:
            print(f"[Admin Error] {e}")

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
