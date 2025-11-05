# cogs/invite_command.py
import discord
from discord.ext import commands
from discord import app_commands
from utils.brand import COLOR, EMOJI_PRIMARY, EMOJI_HIGHLIGHT, footer

# Minimal permission set Zephyra actually uses:
# View Channel (1024), Send Messages (2048), Add Reactions (64),
# Manage Messages (8192) -> needed to remove users' reactions after translating,
# Embed Links (16384), Read Message History (65536),
# Use External Emojis (262144) -> helpful if you ever use cross-server emojis
MINIMAL_PERMS = 1024 + 2048 + 64 + 8192 + 16384 + 65536 + 262144  # 355392
ADMIN_PERMS = 8  # Administrator

def build_invite_link(app_id: int, perms: int) -> str:
    return (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={app_id}"
        f"&permissions={perms}"
        f"&scope=bot%20applications.commands"
    )

class Invite(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="invite", description="DMs you an invite link to add Zephyra to your server.")
    async def invite(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        app_id = interaction.client.user.id if interaction.client and interaction.client.user else None
        if app_id is None:
            return await interaction.followup.send("❌ Could not resolve application ID.", ephemeral=True)

        url_min = build_invite_link(app_id, MINIMAL_PERMS)
        url_admin = build_invite_link(app_id, ADMIN_PERMS)

        embed = discord.Embed(
            title=f"{EMOJI_PRIMARY} Invite Zephyra",
            color=COLOR,
            description=(
                f"Use one of the buttons below to invite **Zephyra**.\n\n"
                f"{EMOJI_HIGHLIGHT} **Recommended (Minimal)** — just the permissions the bot needs.\n"
                f"🛡️ **Administrator** — easier for busy setups, full control.\n"
            ),
        )
        embed.set_footer(text=footer())

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Invite (Recommended)", style=discord.ButtonStyle.link, url=url_min))
        view.add_item(discord.ui.Button(label="Invite (Admin)", style=discord.ButtonStyle.link, url=url_admin))

        # DM the user with the buttons
        try:
            await interaction.user.send(embed=embed, view=view)
            await interaction.followup.send("📩 I’ve sent you a DM with invite buttons.", ephemeral=True)
        except Exception:
            await interaction.followup.send(
                "❌ I couldn’t DM you (privacy settings). Here are the invite links:",
                ephemeral=True,
                view=view
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(Invite(bot))