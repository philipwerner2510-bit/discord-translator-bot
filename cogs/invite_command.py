# cogs/invite_command.py
import discord
from discord import app_commands
from discord.ext import commands
from utils.brand import NAME, COLOR, INVITE_TITLE, FOOTER

# Build a sensible permission set (required + helpful)
PERMISSIONS_INT = (
    discord.Permissions(
        view_channel=True,
        send_messages=True,
        embed_links=True,
        add_reactions=True,
        read_message_history=True,
        use_application_commands=True,
        manage_messages=True,                # optional but helpful for cleanup
        manage_emojis_and_stickers=True,     # optional for future features
        connect=True, speak=True             # optional for future voice features
    ).value
)

REQUIRED = [
    "View Channels",
    "Send Messages",
    "Embed Links",
    "Add Reactions",
    "Read Message History",
    "Use Application Commands",
]
OPTIONAL = [
    "Manage Messages (cleanup)",
    "Manage Emojis & Stickers (future)",
    "Connect/Speak (future voice)",
]

class InviteCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="invite", description=f"Get an invite link to add {NAME} to a server.")
    async def invite(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        bot_id = self.bot.user.id
        invite_url = (
            f"https://discord.com/oauth2/authorize?"
            f"client_id={bot_id}&permissions={PERMISSIONS_INT}&scope=bot%20applications.commands"
        )

        req = "• " + "\n• ".join(REQUIRED)
        opt = "• " + "\n• ".join(OPTIONAL)

        embed = discord.Embed(
            title=INVITE_TITLE,
            description=(
                f"Click the button below to invite **{NAME}** to your server.\n\n"
                f"**Required permissions**\n{req}\n\n"
                f"**Optional permissions**\n{opt}"
            ),
            color=COLOR
        )
        embed.set_footer(text=FOOTER)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label=f"Invite {NAME}",
            url=invite_url,
            style=discord.ButtonStyle.link
        ))

        try:
            await interaction.user.send(embed=embed, view=view)
            await interaction.followup.send("I sent you a DM with the invite link.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(
                f"I couldn't DM you. Here’s the link instead:\n{invite_url}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(InviteCommand(bot))
