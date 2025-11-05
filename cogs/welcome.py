import os
import discord
from discord.ext import commands
from discord import app_commands
from utils.brand import COLOR, EMOJI_PRIMARY, EMOJI_HIGHLIGHT, EMOJI_ACCENT, footer

OWNER_ID = int(os.getenv("OWNER_ID", "762267166031609858"))

def guide_embed() -> discord.Embed:
    e = discord.Embed(
        title=f"{EMOJI_PRIMARY} Welcome to Zephyra — Quick Start",
        description="Make multilingual chat effortless in a minute.",
        color=COLOR,
    )
    e.add_field(
        name="For Everyone",
        value=(
            f"{EMOJI_HIGHLIGHT} React to a message with Zephyra’s emote to get a **DM translation**.\n"
            f"{EMOJI_ACCENT} Set your personal language: **`/setmylang <code>`** (autocomplete).\n"
            f"{EMOJI_HIGHLIGHT} Translate text: **`/translate <text> <target_lang>`**.\n"
            "🏓 **/ping** to check responsiveness."
        ),
        inline=False,
    )
    e.add_field(
        name="For Admins (60s setup)",
        value=(
            "• Choose watched channels: **`/channelselection`**\n"
            "• Default language: **`/defaultlang <code>`**\n"
            "• Reaction emote (Unicode or this server’s custom): **`/emote <emoji>`**\n"
            "• Error logs (optional): **`/seterrorchannel <#channel | none>`**\n"
            "• Review config: **`/settings`**"
        ),
        inline=False,
    )
    e.add_field(
        name="Tips",
        value=(
            "• Use common codes like `en`, `de`, `fr`.\n"
            "• Prefer this server’s custom emoji for `/emote`.\n"
            "• Zephyra reacts only in channels from **`/channelselection`**."
        ),
        inline=False,
    )
    e.set_footer(text=footer())
    return e

class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        embed = guide_embed()
        target = None
        for ch in guild.text_channels:
            perms = ch.permissions_for(guild.me)
            if perms.send_messages and perms.view_channel and perms.embed_links:
                target = ch
                break
        if target:
            try:
                await target.send(embed=embed)
            except Exception as e:
                print(f"[welcome] Could not send welcome in {guild.name}: {e}")

    @app_commands.guild_only()
    @app_commands.command(name="guide", description="Post Zephyra’s quick-start guide in this channel (admins only).")
    async def guide(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator and interaction.user.id != OWNER_ID:
            return await interaction.response.send_message("❌ Admins only.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        embed = guide_embed()
        try:
            await interaction.channel.send(embed=embed)
            await interaction.followup.send("✅ Posted the guide.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Could not send here: `{e}`", ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="guidepreview", description="Preview Zephyra’s quick-start guide (ephemeral).")
    async def guidepreview(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator and interaction.user.id != OWNER_ID:
            return await interaction.response.send_message("❌ Admins only.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(embed=guide_embed(), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))