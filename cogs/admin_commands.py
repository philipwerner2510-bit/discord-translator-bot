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
    @app_commands.command(name="defaultlang", description="Set the default translation language for this server.")
    async def defaultlang(self, interaction: discord.Interaction, lang: str):
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.HTTPException:
            pass  # Interaction already acknowledged

        try:
            guild_id = interaction.guild.id if interaction.guild else None
            if guild_id is None:
                await interaction.followup.send("❌ Cannot set default language outside a server.", ephemeral=True)
                return
            await database.set_server_lang(guild_id, lang.lower())
            await interaction.followup.send(f"✅ Server default language set to `{lang}`.", ephemeral=True)
        except Exception as e:
            await self.safe_error(interaction, e)

    # -----------------------
    # Set translation channels with multiple-choice menu
    # -----------------------
    @app_commands.command(name="channelselection", description="Select channels where the bot reacts to messages for translation.")
    @app_commands.guild_only()
    async def channelselection(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.HTTPException:
            pass

        try:
            guild = interaction.guild
            if not guild:
                await interaction.followup.send("❌ Cannot select channels outside a server.", ephemeral=True)
                return

            options = [
                discord.SelectOption(label=ch.name, value=str(ch.id))
                for ch in guild.text_channels
            ]

            select = discord.ui.Select(
                placeholder="Select channels for translation",
                min_values=1,
                max_values=len(options),
                options=options
            )

            async def callback(select_interaction: discord.Interaction):
                selected_ids = [int(cid) for cid in select.values]
                await database.set_translation_channels(guild.id, selected_ids)
                await select_interaction.response.send_message(f"✅ Translation channels set: {', '.join([guild.get_channel(cid).mention for cid in selected_ids if guild.get_channel(cid)])}", ephemeral=True)

            select.callback = callback
            view = discord.ui.View()
            view.add_item(select)
            await interaction.followup.send("Select the channels for translation:", view=view, ephemeral=True)

        except Exception as e:
            await self.safe_error(interaction, e)

    # -----------------------
    # Set error channel
    # -----------------------
    @app_commands.command(name="seterrorchannel", description="Define the error logging channel for your server.")
    async def seterrorchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.HTTPException:
            pass

        try:
            guild_id = interaction.guild.id if interaction.guild else None
            if guild_id is None:
                await interaction.followup.send("❌ Cannot set error channel outside a server.", ephemeral=True)
                return
            await database.set_error_channel(guild_id, channel.id)
            await interaction.followup.send(f"✅ Error channel set to {channel.mention}.", ephemeral=True)
        except Exception as e:
            await self.safe_error(interaction, e)

    # -----------------------
    # Set bot emote
    # -----------------------
    @app_commands.command(name="emote", description="Set the bot's reaction emote for translation channels.")
    async def emote(self, interaction: discord.Interaction, emote: str):
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.HTTPException:
            pass

        try:
            guild_id = interaction.guild.id if interaction.guild else None
            if guild_id is None:
                await interaction.followup.send("❌ Cannot set emote outside a server.", ephemeral=True)
                return
            await database.set_bot_emote(guild_id, emote)
            await interaction.followup.send(f"✅ Bot reaction emote set to {emote}.", ephemeral=True)
        except Exception as e:
            await self.safe_error(interaction, e)

    # -----------------------
    # Centralized error handler
    # -----------------------
    async def safe_error(self, interaction: discord.Interaction, error):
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Error: {error}", ephemeral=True)
        except discord.HTTPException:
            # Already acknowledged; log to console as last resort
            print(f"[AdminCommands Error] {error}")

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
