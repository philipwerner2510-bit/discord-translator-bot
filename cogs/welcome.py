# cogs/welcome.py
import discord
from discord.ext import commands
from discord import app_commands
from utils.brand import NAME, COLOR, GUIDE_TITLE, FOOTER

def build_guide_embed(guild_name: str) -> discord.Embed:
    e = discord.Embed(
        title=GUIDE_TITLE,
        description=(
            f"Thanks for adding **{NAME}** to **{guild_name}**!\n\n"
            "**Quick setup (2–3 mins):**\n"
            "1) `/channelselection` → choose where reactions should trigger translations.\n"
            "2) `/defaultlang <lang>` → set the server’s default target language.\n"
            "3) Optional: `/aisettings <true|false>` → enable AI fallback for tricky text & slang.\n\n"
            "**Tips for members:**\n"
            "• Use `/setmylang <lang>` to set your own language.\n"
            "• React to a message in selected channels to get a DM with the translation.\n"
            "• `/help` shows all commands.\n"
        ),
        color=COLOR
    )
    e.add_field(
        name="Admin tools",
        value=(
            "• `/settings` — current configuration\n"
            "• `/librestatus` — Libre endpoint health\n"
            "• `/stats` — usage counters\n"
            "• `/leaderboard` — top translators\n"
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
        guild_name = interaction.guild.name if interaction.guild else "this server"
        embed = build_guide_embed(guild_name)
        try:
            await interaction.channel.send(embed=embed)
            await interaction.followup.send("Posted the guide in this channel.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Could not post here: {e}", ephemeral=True)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Post the guide once when Zephyra joins a new server."""
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
