# cogs/welcome.py
import os
import discord
from discord.ext import commands
from discord import app_commands

BOT_COLOR = 0xDE002A
OWNER_ID = 762267166031609858

def build_invite_url(app_id: int) -> str:
    perms = 274878188544
    return f"https://discord.com/oauth2/authorize?client_id={app_id}&permissions={perms}&scope=bot%20applications.commands"

def guide_embed() -> discord.Embed:
    e = discord.Embed(
        title="👋 Welcome to Demon Translator",
        color=BOT_COLOR,
        description=(
            "Thanks for adding me to your server! Here’s how to use me:\n\n"
            "✅ **React** to any message with the bot emote → Get the translation in DMs\n"
            "✅ Set your language using **/setmylang** (clean dropdown)\n"
            "✅ Translate custom text with **/translate <text>**\n"
            "✅ See this menu anytime with **/guide** or **/help**\n"
        )
    )
    e.add_field(
        name="✨ Useful Commands",
        value=(
            "• `/setmylang` — choose your translation language\n"
            "• `/translate <text>` — manual translation\n"
            "• `/ping` — latency check\n"
            "• `/help` — full User/Admin/Owner command menu\n"
            "• `/langlist` — language code list"
        ),
        inline=False
    )
    e.set_footer(text="Demon Translator © by Polarix1954 😈🔥")
    return e

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -----------------------
    # /guide (Admin Only)
    # -----------------------
    @app_commands.command(name="guide", description="Send the guide embed in this channel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def guide_cmd(self, interaction: discord.Interaction):
        app_id = self.bot.user.id
        invite_url = build_invite_url(app_id)
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="➕ Invite Me", url=invite_url))

        await interaction.response.send_message(embed=guide_embed(), view=view)
    
    @guide_cmd.error
    async def guide_cmd_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ Only admins can send the guide.", ephemeral=True)

    # -----------------------
    # Auto-DM when joining new server
    # -----------------------
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        app_id = self.bot.user.id
        invite_url = build_invite_url(app_id)
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="➕ Invite Me", url=invite_url))

        # Try DM guild owner first
        try:
            await guild.owner.send(embed=guide_embed(), view=view)
            return
        except:
            pass

        # Otherwise send to first channel bot can speak in
        for ch in guild.text_channels:
            if ch.permissions_for(guild.me).send_messages:
                await ch.send(embed=guide_embed(), view=view)
                break

async def setup(bot):
    await bot.add_cog(Welcome(bot))