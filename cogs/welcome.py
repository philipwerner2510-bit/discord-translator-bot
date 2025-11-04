# cogs/welcome.py
import discord
from discord.ext import commands
from discord import app_commands

BOT_COLOR = 0xDE002A  # same red as your other embeds

def build_user_welcome_embed(guild: discord.Guild) -> discord.Embed:
    e = discord.Embed(
        title="😈 Demon Translator — Quick Start",
        color=BOT_COLOR,
        description=(
            "Welcome to **Demon Translator**! Here’s how to use me:\n\n"
            "• **Set your language** → `/setmylang` (pick from a dropdown or type a code)\n"
            "• **Translate manually** → `/translate <text> <lang>`\n"
            "• **See languages** → `/langlist` (flags + names)\n"
            "• **Trigger translations** → in selected channels, react to a message with the bot’s emoji\n"
            "• **Check me** → `/ping`, `/test`\n\n"
            "**Tip:** If you react and don’t get a DM, enable “Allow direct messages” in your Privacy settings."
        )
    )
    e.set_footer(text="Created by Polarix1954")
    return e

def build_admin_quick_guide_embed(guild: discord.Guild) -> discord.Embed:
    e = discord.Embed(
        title="🛠 Admin Guide — Demon Translator",
        color=BOT_COLOR,
        description=(
            "Quick setup (Admins):\n"
            "1) **Pick channels** → `/channelselection`\n"
            "2) **Default language** → `/defaultlang` (supports dropdown)\n"
            "3) **Trigger emoji** → `/emote 🔃` (or a custom server emoji)\n"
            "4) **Error channel** → `/seterrorchannel #channel`\n"
            "5) **Permissions** → Bot needs **View Channel**, **Read Message History**, **Add Reactions** "
            "(and **Manage Messages** only to remove users’ reactions)\n\n"
            "Use `/settings` to review configuration at any time."
        )
    )
    e.set_footer(text="Only visible to server admins")
    return e


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Auto-send the user quick-start when joining a new server
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        embed = build_user_welcome_embed(guild)

        # Prefer system channel if sendable
        target = None
        if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
            target = guild.system_channel
        else:
            # fallback: first text channel where the bot can speak
            for ch in guild.text_channels:
                perms = ch.permissions_for(guild.me)
                if perms.view_channel and perms.send_messages:
                    target = ch
                    break

        if target:
            try:
                await target.send(embed=embed)
            except Exception:
                pass  # don’t crash if channel is locked right after join

    # Admin-only /guide (ephemeral by default)
    @app_commands.command(name="guide", description="Admin quick setup guide.")
    @app_commands.default_permissions(manage_guild=True)
    async def guide_cmd(self, interaction: discord.Interaction):
        embed = build_admin_quick_guide_embed(interaction.guild)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Welcome(bot))