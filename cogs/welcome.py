# cogs/welcome.py
import discord
from discord.ext import commands
from discord import app_commands

BOT_COLOR = 0xDE002A  # consistent with your other embeds

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


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Auto-send the user quick-start when joining a new server
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        embed = build_user_welcome_embed(guild)

        # Prefer the system channel if we can speak there
        target = None
        if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
            target = guild.system_channel
        else:
            # fallback: first text channel with send permission
            for ch in guild.text_channels:
                perms = ch.permissions_for(guild.me)
                if perms.view_channel and perms.send_messages:
                    target = ch
                    break

        if target:
            try:
                await target.send(embed=embed)
            except Exception:
                pass  # ignore if channel gets locked or deleted right after join

    # /guide: Admins can post the same user-facing Quick Start embed to a channel
    @app_commands.command(
        name="guide",
        description="Post the Demon Translator Quick Start for everyone to read (admins only)."
    )
    @app_commands.default_permissions(manage_guild=True)
    async def guide_cmd(self, interaction: discord.Interaction):
        embed = build_user_welcome_embed(interaction.guild)

        # Try to post publicly in the current channel
        try:
            await interaction.response.send_message(embed=embed)  # public message
        except discord.Forbidden:
            # Fallback if we can't speak here: send ephemeral notice with a button to pick another channel
            view = discord.ui.View()
            # Build a dropdown of channels we CAN send to
            options = []
            for ch in interaction.guild.text_channels[:25]:
                perms = ch.permissions_for(interaction.guild.me)
                if perms.view_channel and perms.send_messages:
                    options.append(discord.SelectOption(label=f"#{ch.name}", value=str(ch.id)))
            if options:
                select = discord.ui.Select(
                    placeholder="Choose a channel I can speak in…",
                    min_values=1, max_values=1, options=options
                )

                async def on_select(itx: discord.Interaction):
                    if itx.user.id != interaction.user.id:
                        return await itx.response.defer()
                    channel_id = int(select.values[0])
                    channel = interaction.guild.get_channel(channel_id)
                    try:
                        await channel.send(embed=embed)
                        await itx.response.edit_message(
                            content=f"✅ Posted the guide in {channel.mention}.",
                            view=None
                        )
                    except Exception as e:
                        await itx.response.edit_message(
                            content=f"❌ Couldn't send to <#{channel_id}>: {e}",
                            view=None
                        )

                select.callback = on_select
                view.add_item(select)
                await interaction.response.send_message(
                    content="I can’t send a public message here. Pick another channel:",
                    view=view,
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "❌ I don’t have permission to speak in any text channel.",
                    ephemeral=True
                )


async def setup(bot):
    await bot.add_cog(Welcome(bot))