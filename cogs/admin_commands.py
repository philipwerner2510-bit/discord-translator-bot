import discord
from discord.ext import commands
from discord import app_commands
from utils import database

BOT_COLOR = 0xde002a

SUPPORTED_LANGS = ["en","de","es","fr","it","ja","ko","zh"]

def is_admin():
    def predicate(interaction: discord.Interaction):
        return interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)


class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ✅ Set default server language
    @is_admin()
    @app_commands.command(name="defaultlang", description="Set the default translation language for this server.")
    async def defaultlang(self, interaction: discord.Interaction, lang: str):
        await interaction.response.defer(ephemeral=True)
        lang = lang.lower()

        if lang not in SUPPORTED_LANGS:
            return await interaction.followup.send(
                f"❌ Invalid language. Supported: {', '.join(SUPPORTED_LANGS)}",
                ephemeral=True
            )

        await database.set_server_lang(interaction.guild.id, lang)
        await interaction.followup.send(
            f"✅ Default server language set to `{lang}`.",
            ephemeral=True
        )

    # ✅ Channel selection stays same
    @is_admin()
    @app_commands.command(name="channelselection", description="Choose channels where translations are active.")
    async def channelselection(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        options = [
            discord.SelectOption(label=ch.name, value=str(ch.id))
            for ch in guild.text_channels
        ]

        select = discord.ui.Select(
            placeholder="Select translation channels...",
            min_values=1,
            max_values=min(25, len(options)),
            options=options
        )

        async def cb(inter: discord.Interaction):
            ids = list(map(int, select.values))
            await database.set_translation_channels(guild.id, ids)
            txt = ", ".join(f"<#{i}>" for i in ids)
            await inter.response.send_message(
                f"✅ Translation enabled in: {txt}",
                ephemeral=True
            )

        select.callback = cb
        view = discord.ui.View()
        view.add_item(select)
        await interaction.followup.send("Select channels:", view=view, ephemeral=True)

    # ✅ Error channel stays same
    @is_admin()
    @app_commands.command(name="seterrorchannel", description="Set a channel where AI warnings & errors appear.")
    async def seterrorchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await database.set_error_channel(interaction.guild.id, channel.id)
        await interaction.response.send_message(
            f"✅ Error channel set to {channel.mention}",
            ephemeral=True
        )

    # ✅ New: AI settings command
    @is_admin()
    @app_commands.command(name="aisettings", description="Enable or disable AI translations for this server.")
    async def aisettings(self, interaction: discord.Interaction, enabled: bool):
        await interaction.response.defer(ephemeral=True)
        gid = interaction.guild.id

        await database.set_ai_enabled(gid, enabled)

        status = "🧠 AI Enabled ✅" if enabled else "⚙️ AI Disabled — Google fallback active"
        await interaction.followup.send(status, ephemeral=True)

    # ✅ View settings
    @is_admin()
    @app_commands.command(name="settings", description="View translation settings for this server.")
    async def settings(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        gid = interaction.guild.id

        default = await database.get_server_lang(gid) or "Not set"
        error = await database.get_error_channel(gid)
        ai_en = await database.get_ai_enabled(gid)

        ai_status = "🧠 Enabled" if ai_en else "⚙️ Disabled"

        embed = discord.Embed(
            title="🛠️ Server Settings",
            color=BOT_COLOR
        )
        embed.add_field(name="Default Language", value=default, inline=True)
        embed.add_field(name="AI Mode", value=ai_status, inline=True)
        embed.add_field(
            name="Error Channel",
            value=f"<#{error}>" if error else "Not set",
            inline=False
        )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))