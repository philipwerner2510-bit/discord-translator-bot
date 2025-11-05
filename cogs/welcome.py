# cogs/welcome.py
import os
import discord
from discord.ext import commands
from discord import app_commands

OWNER_ID = int(os.getenv("OWNER_ID", "762267166031609858"))
BRAND_COLOR = 0x00E6F6  # Zephyra cyan

def build_guide_embed(guild: discord.Guild | None) -> discord.Embed:
    e = discord.Embed(
        title="Welcome to Zephyra — Quick Start",
        description=(
            "Zephyra makes multilingual chat effortless. Here’s how to use her in your server."
        ),
        color=BRAND_COLOR,
    )

    # 1) For everyone
    e.add_field(
        name="For Everyone",
        value=(
            "• **React to a message** with Zephyra’s emote to get a **DM translation** in your language.\n"
            "• Set your personal language with **`/setmylang <code>`** (autocomplete supported).\n"
            "• Translate specific text manually using **`/translate <text> <target_lang>`**.\n"
            "• Check responsiveness with **`/ping`**."
        ),
        inline=False,
    )

    # 2) For admins (short)
    e.add_field(
        name="For Admins (Setup in 60s)",
        value=(
            "• Choose channels Zephyra should watch: **`/channelselection`**.\n"
            "• Set server default language (fallback for users): **`/defaultlang <code>`**.\n"
            "• Pick the reaction emote (Unicode or **this server’s** custom emoji): **`/emote <emoji>`**.\n"
            "• Optional error logs channel: **`/seterrorchannel <#channel | none>`**.\n"
            "• Review settings: **`/settings`**."
        ),
        inline=False,
    )

    # 3) Tips
    e.add_field(
        name="Tips",
        value=(
            "• Use **two or three language codes** most often (e.g., `en`, `de`, `fr`).\n"
            "• Prefer **server custom emoji** for `/emote` to avoid missing permissions.\n"
            "• Zephyra only reacts in channels selected via **`/channelselection`**."
        ),
        inline=False,
    )

    # Footer
    e.set_footer(text="Created by @Polarix1954")
    return e


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Auto-send the same guide on join (first text channel with send perms)
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        embed = build_guide_embed(guild)
        # Find a channel where the bot can speak
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

    # Admin-only: publish the guide in the current channel
    @app_commands.guild_only()
    @app_commands.command(name="guide", description="Post Zephyra’s quick-start guide in this channel (admins only).")
    async def guide(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator and interaction.user.id != OWNER_ID:
            return await interaction.response.send_message("❌ Admins only.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        embed = build_guide_embed(interaction.guild)
        try:
            await interaction.channel.send(embed=embed)  # public post
            await interaction.followup.send("✅ Posted the guide in this channel.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Could not send the guide here: `{e}`", ephemeral=True)

    # Admin-only: preview the guide privately
    @app_commands.guild_only()
    @app_commands.command(name="guidepreview", description="Preview Zephyra’s quick-start guide (ephemeral).")
    async def guidepreview(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator and interaction.user.id != OWNER_ID:
            return await interaction.response.send_message("❌ Admins only.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        embed = build_guide_embed(interaction.guild)
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))