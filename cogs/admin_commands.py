# cogs/admin_commands.py
import re
import discord
from discord.ext import commands
from discord import app_commands
from utils import database
from utils.brand import COLOR
from cogs.translate import SUPPORTED_LANGS, LANG_LOOKUP, _filter_lang_choices

CUSTOM_EMOJI_RE = re.compile(r"<(a?):([a-zA-Z0-9_]+):(\d+)>")

# ---------- Autocomplete helpers (must be async) ----------
async def server_lang_autocomplete(_interaction: discord.Interaction, current: str):
    return _filter_lang_choices(current)

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -----------------------
    # defaultlang (with autocomplete)
    # -----------------------
    @app_commands.guild_only()
    @app_commands.autocomplete(lang=server_lang_autocomplete)
    @app_commands.command(name="defaultlang", description="Set the default translation language for this server.")
    async def defaultlang(self, interaction: discord.Interaction, lang: str):
        await interaction.response.defer(ephemeral=True)
        code = lang.lower()
        if code not in SUPPORTED_LANGS:
            return await interaction.followup.send("❌ Unsupported language. Please pick from the list.", ephemeral=True)
        await database.set_server_lang(interaction.guild.id, code)
        flag, name = LANG_LOOKUP.get(code, ("🏳️", code))
        await interaction.followup.send(f"Server default language set to **{name} ({code}) {flag}**.", ephemeral=True)

    # -----------------------
    # channelselection
    # -----------------------
    @app_commands.guild_only()
    @app_commands.command(name="channelselection", description="Select channels where the bot reacts to messages for translation.")
    async def channelselection(self, interaction: discord.Interaction):
        guild = interaction.guild
        options = [discord.SelectOption(label=ch.name, value=str(ch.id)) for ch in guild.text_channels][:25]
        select = discord.ui.Select(
            placeholder="Select translation channels...",
            min_values=1,
            max_values=len(options),
            options=options
        )
        async def select_callback(it: discord.Interaction):
            selected_ids = [int(val) for val in select.values]
            await database.set_translation_channels(guild.id, selected_ids)
            mentions = ", ".join(f"<#{id}>" for id in selected_ids)
            await it.response.send_message(f"Translation channels set: {mentions}", ephemeral=True)
        select.callback = select_callback
        view = discord.ui.View(timeout=60); view.add_item(select)
        await interaction.response.send_message("Select the channels for translation:", view=view, ephemeral=True)

    # -----------------------
    # seterrorchannel
    # -----------------------
    @app_commands.guild_only()
    @app_commands.command(name="seterrorchannel", description="Define the error logging channel. Use 'none' to remove.")
    async def seterrorchannel(self, interaction: discord.Interaction, channel: str):
        gid = interaction.guild.id
        if channel.lower() == "none":
            await database.set_error_channel(gid, None)
            return await interaction.response.send_message("Error channel removed.", ephemeral=True)
        target = None
        try:
            if channel.startswith("<#") and channel.endswith(">"):
                cid = int(channel[2:-1]); target = interaction.guild.get_channel(cid)
            else:
                cid = int(channel); target = interaction.guild.get_channel(cid)
        except Exception:
            target = None
        if not target:
            return await interaction.response.send_message("❌ Invalid channel.", ephemeral=True)
        await database.set_error_channel(gid, target.id)
        await interaction.response.send_message(f"Error channel set to {target.mention}.", ephemeral=True)

    # -----------------------
    # emote
    # -----------------------
    @app_commands.guild_only()
    @app_commands.command(name="emote", description="Set the bot's reaction emote for translation channels.")
    async def emote(self, interaction: discord.Interaction, emote: str):
        await database.set_bot_emote(interaction.guild.id, emote.strip())
        await interaction.response.send_message(f"Reaction emote set to {emote}.", ephemeral=True)

    # -----------------------
    # settings (with permission diagnostics)
    # -----------------------
    @app_commands.guild_only()
    @app_commands.command(name="settings", description="Show current server settings for the bot.")
    async def settings(self, interaction: discord.Interaction):
        gid = interaction.guild.id
        default_lang = await database.get_server_lang(gid) or "Not set"
        emote = await database.get_bot_emote(gid) or "🔁"
        err_ch_id = await database.get_error_channel(gid)
        err = interaction.guild.get_channel(err_ch_id).mention if err_ch_id and interaction.guild.get_channel(err_ch_id) else "Not set"
        channels = await database.get_translation_channels(gid)
        ch_txt = ", ".join(f"<#{c}>" for c in channels) if channels else "None"
        ai_enabled = await database.get_ai_enabled(gid)

        embed = discord.Embed(title="Server Settings", color=COLOR)
        embed.add_field(name="Default Language", value=default_lang, inline=False)
        embed.add_field(name="Bot Emote", value=emote, inline=True)
        embed.add_field(name="Error Channel", value=err, inline=True)
        embed.add_field(name="Translation Channels", value=ch_txt, inline=False)
        embed.add_field(name="AI Fallback", value="Enabled" if ai_enabled else "Disabled", inline=True)

        # ---- Permission diagnostics (for current channel) ----
        me = interaction.guild.me
        def mark(ok): return "✅" if ok else "⚠️"
        if me:
            cperms = interaction.channel.permissions_for(me)
            embed.add_field(
                name="Channel Permissions (here)",
                value=(
                    f"{mark(cperms.send_messages)} Send Messages\n"
                    f"{mark(cperms.embed_links)} Embed Links\n"
                    f"{mark(cperms.add_reactions)} Add Reactions\n"
                    f"{mark(cperms.read_message_history)} Read Message History\n"
                ),
                inline=False
            )
            gperms = me.guild_permissions
            embed.add_field(
                name="Guild Permissions",
                value=(
                    f"{mark(gperms.manage_roles)} Manage Roles\n"
                    f"{mark(gperms.manage_emojis)} Manage Emojis & Stickers\n"
                    f"{mark(gperms.use_application_commands)} Use Application Commands\n"
                ),
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # -----------------------
    # aisettings
    # -----------------------
    @app_commands.command(name="aisettings", description="Enable or disable AI fallback.")
    @app_commands.describe(enabled="true to enable, false to disable")
    async def aisettings(self, interaction: discord.Interaction, enabled: bool):
        if not interaction.guild or not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Admins only.", ephemeral=True)
        await database.set_ai_enabled(interaction.guild.id, enabled)
        await interaction.response.send_message(f"AI fallback is now **{'enabled' if enabled else 'disabled'}**.", ephemeral=True)

    # -----------------------
    # NEW: /permissions (admin) — check channel + guild perms
    # -----------------------
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
        name="permissions",
        description="(Admin) Check Zephyra's permissions here or in a selected channel."
    )
    @app_commands.describe(channel="Optional: channel to check (defaults to this channel).")
    async def permissions(self, interaction: discord.Interaction, channel: discord.TextChannel | None = None):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        me = guild.me
        target_channel = channel or interaction.channel

        if not me:
            return await interaction.followup.send("Couldn't resolve my member object in this server.", ephemeral=True)

        def mark(ok): return "✅" if ok else "⚠️"

        # Channel perms (target channel)
        cperms = target_channel.permissions_for(me)
        chan_report = [
            (cperms.view_channel, "View Channel"),
            (cperms.send_messages, "Send Messages"),
            (cperms.embed_links, "Embed Links"),
            (cperms.add_reactions, "Add Reactions"),
            (cperms.read_message_history, "Read Message History"),
            (cperms.use_application_commands, "Use Application Commands"),
        ]
        chan_missing = [name for ok, name in chan_report if not ok]

        # Guild perms
        gperms = me.guild_permissions
        guild_report = [
            (gperms.manage_roles, "Manage Roles"),
            (gperms.manage_emojis, "Manage Emojis & Stickers"),
            (gperms.manage_messages, "Manage Messages"),
        ]
        guild_missing = [name for ok, name in guild_report if not ok]

        embed = discord.Embed(
            title="Permission Check",
            description=f"Target channel: {target_channel.mention}",
            color=COLOR
        )

        embed.add_field(
            name="Channel Permissions",
            value="\n".join(f"{mark(ok)} {name}" for ok, name in chan_report),
            inline=False
        )
        embed.add_field(
            name="Guild Permissions",
            value="\n".join(f"{mark(ok)} {name}" for ok, name in guild_report),
            inline=False
        )

        if chan_missing or guild_missing:
            tips = []
            if chan_missing:
                tips.append("**Channel**: " + ", ".join(chan_missing))
            if guild_missing:
                tips.append("**Guild**: " + ", ".join(guild_missing))
            embed.add_field(
                name="Missing",
                value="\n".join(tips),
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
