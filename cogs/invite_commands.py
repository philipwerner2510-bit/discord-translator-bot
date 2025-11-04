import discord
from discord import app_commands
from discord.ext import commands
import os

# Permissions Calculator:
# Required perms + optional perms
PERMISSIONS_INT = (
    discord.Permissions(
        view_channel=True,
        send_messages=True,
        embed_links=True,
        add_reactions=True,
        read_message_history=True,
        use_application_commands=True,
        manage_messages=True,   # optional but helpful
        manage_emojis_and_stickers=True,  # optional future
        connect=True,  # future voice translation
        speak=True
    ).value
)

class InviteCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="invite", description="Get an invite link to add Demon Translator to another server!")
    async def invite(self, interaction: discord.Interaction):
        user = interaction.user
        await interaction.response.defer(ephemeral=True)

        bot_id = self.bot.user.id
        invite_url = (
            f"https://discord.com/oauth2/authorize?"
            f"client_id={bot_id}&permissions={PERMISSIONS_INT}&scope=bot%20applications.commands"
        )

        embed = discord.Embed(
            title="🛡️ Invite Demon Translator",
            description=(
                "Thanks for spreading the chaos 😈🔥\n\n"
                "Click below to invite Demon Translator to another server!"
            ),
            color=0xde002a
        )
        embed.set_footer(text="Summoned by Polarix’s loyal followers 🩸")

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="➕ Invite Demon Translator",
                url=invite_url,
                style=discord.ButtonStyle.link
            )
        )

        # DM the user
        try:
            await user.send(embed=embed, view=view)
            await interaction.followup.send("✅ I sent you a DM with the invite link!", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(
                f"⚠️ I couldn't DM you! Here's the link instead:\n{invite_url}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(InviteCommand(bot))
