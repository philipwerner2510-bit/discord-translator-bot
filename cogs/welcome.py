# cogs/welcome.py
import discord
from discord.ext import commands
from discord import app_commands
from utils.brand import NAME, COLOR, GUIDE_TITLE, FOOTER

def build_guide_embed(guild_name: str) -> discord.Embed:
    e = discord.Embed(
        title=GUIDE_TITLE,
        description=(
            f"Thank you for inviting **{NAME}**.\n\n"
            "**Quick setup:**\n"
            "1) `/channelselection` → choose channels for reactions.\n"
            "2) `/defaultlang` → set the server’s default target language.\n"
            "3) Optional: `/aisettings true|false` → enable AI fallback for best quality.\n"
            "4) Use `/help` for the full command reference.\n"
        ),
        color=COLOR
    )
    e.add_field(
        name="Tips",
        value=(
            "• Users set personal language via `/setmylang`.\n"
            "• React in selected channels to receive translations.\n"
            "• `/stats` and `/leaderboard` show activity.\n"
        ),
        inline=False
    )
    e.set_footer(text=FOOTER)
    return e

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="guide", description="(Admin) Post the quick-start guide here.")
    @app_commands.checks.has_permissions(administrator=True)
    async def guide(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = build_guide_embed(interaction.guild.name if interaction.guild else "your server")
        try:
            await interaction.channel.send(embed=embed)
            await interaction.followup.send("Posted the guide.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Could not post here: {e}", ephemeral=True)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        embed = build_guide_embed(guild.name)
        for ch in guild.text_channels:
            try:
                perms = ch.permissions_for(guild.me)
                if perms.send_messages and perms.embed_links:
                    await ch.send(embed=embed)
                    break
            except Exception:
                continue

async def setup(bot):
    await bot.add_cog(Welcome(bot))
