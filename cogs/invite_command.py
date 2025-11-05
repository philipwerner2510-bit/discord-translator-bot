import discord
from discord.ext import commands
from discord import app_commands
from utils.brand import COLOR, INVITE_TITLE, footer, Z_EXCITED

MIN_PERMS = 1024 + 2048 + 64 + 8192 + 16384 + 65536 + 262144
ADMIN_PERMS = 8

def link(app_id:int, perms:int)->str:
    return f"https://discord.com/api/oauth2/authorize?client_id={app_id}&permissions={perms}&scope=bot%20applications.commands"

class Invite(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="invite", description="DMs you invite buttons to add Zephyra to your server.")
    async def invite(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        app_id = interaction.client.user.id
        url_min = link(app_id, MIN_PERMS); url_admin = link(app_id, ADMIN_PERMS)
        e = discord.Embed(title=f"{Z_EXCITED} {INVITE_TITLE}", color=COLOR,
                          description="Choose your invite style below.")
        e.set_footer(text=footer())
        v = discord.ui.View()
        v.add_item(discord.ui.Button(label="Invite (Recommended)", style=discord.ButtonStyle.link, url=url_min))
        v.add_item(discord.ui.Button(label="Invite (Admin)", style=discord.ButtonStyle.link, url=url_admin))
        try:
            await interaction.user.send(embed=e, view=v)
            await interaction.followup.send("📩 Check your DMs.", ephemeral=True)
        except Exception:
            await interaction.followup.send(embed=e, view=v, ephemeral=True)

async def setup(bot): await bot.add_cog(Invite(bot))
