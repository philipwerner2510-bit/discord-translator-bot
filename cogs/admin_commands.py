# cogs/admin_commands.py
import re
import discord
from discord.ext import commands
from discord import app_commands
from utils import database
from utils.config import SUPPORTED_LANGS, LANG_META, lang_label

CUSTOM_EMOJI_RE = re.compile(r"<(a?):([a-zA-Z0-9_]+):(\d+)>")


class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -----------------------
    # /defaultlang — polished (typed OR dropdown)
    # -----------------------
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(lang="Language code (e.g., en, de). Leave empty to open a dropdown.")
    @app_commands.command(name="defaultlang", description="Set the server default translation language.")
    async def defaultlang(self, interaction: discord.Interaction, lang: str | None = None):
        gid = interaction.guild.id

        # Typed usage → save directly
        if lang:
            code = lang.lower()
            if code not in SUPPORTED_LANGS:
                return await interaction.response.send_message(
                    f"❌ Unsupported: `{code}`. Try `/langlist` or run `/defaultlang` with no value to pick from a list.",
                    ephemeral=True
                )
            await database.set_server_lang(gid, code)
            flag, name = LANG_META.get(code, ("🌐", code.upper()))
            return await interaction.response.send_message(
                f"✅ Server default language set to **{flag} {name} ({code})**",
                ephemeral=True
            )

        # No-arg usage → open dropdown with flags + names (paginated)
        PER_PAGE = 25
        codes_sorted = sorted(SUPPORTED_LANGS, key=lambda c: LANG_META.get(c, ("🌐", c.upper()))[1])
        pages = [codes_sorted[i:i + PER_PAGE] for i in range(0, len(codes_sorted), PER_PAGE)]
        total_pages = len(pages)

        class PickerView(discord.ui.View):
            def __init__(self, admin_user: discord.User, page_idx: int = 0):
                super().__init__(timeout=60)
                self.admin_user = admin_user
                self.page_idx = page_idx
                self.rebuild()

            def rebuild(self):
                self.clear_items()
                current = pages[self.page_idx]

                options = [
                    discord.SelectOption(
                        label=lang_label(code)[:100],
                        value=code,
                        description=f"Code: {code}"
                    )
                    for code in current
                ]

                select = discord.ui.Select(
                    placeholder=f"Choose default language — Page {self.page_idx + 1}/{total_pages}",
                    min_values=1,
                    max_values=1,
                    options=options
                )

                async def on_select(itx: discord.Interaction):
                    if itx.user.id != self.admin_user.id:
                        return await itx.response.defer()
                    code = select.values[0]
                    await database.set_server_lang(gid, code)
                    flag, name = LANG_META.get(code, ("🌐", code.upper()))
                    await itx.response.edit_message(
                        content=f"✅ Server default language set to **{flag} {name} ({code})**",
                        view=None
                    )
                    self.stop()

                select.callback = on_select
                self.add_item(select)

                if total_pages > 1:
                    @discord.ui.button(label="⬅ Previous", style=discord.ButtonStyle.secondary, disabled=self.page_idx == 0)
                    async def prev_btn(itx: discord.Interaction, button: discord.ui.Button):
                        if itx.user.id != self.admin_user.id:
                            return await itx.response.defer()
                        self.page_idx -= 1
                        self.rebuild()
                        await itx.response.edit_message(content=self.content_text(), view=self)

                    @discord.ui.button(label="Next ➡", style=discord.ButtonStyle.primary, disabled=self.page_idx >= total_pages - 1)
                    async def next_btn(itx: discord.Interaction, button: discord.ui.Button):
                        if itx.user.id != self.admin_user.id:
                            return await itx.response.defer()
                        self.page_idx += 1
                        self.rebuild()
                        await itx.response.edit_message(content=self.content_text(), view=self)

            def content_text(self):
                return "Pick your **server default** translation language 👇"

        view = PickerView(interaction.user)
        await interaction.response.send_message(content=view.content_text(), view=view, ephemeral=True)

    @defaultlang.autocomplete("lang")
    async def _auto_defaultlang(self, interaction: discord.Interaction, current: str):
        cur = (current or "").lower()
        # match by code or by pretty name
        matches = [
            c for c in SUPPORTED_LANGS
            if cur in c or cur in LANG_META.get(c, ("", ""))[1].lower()
        ]
        return [app_commands.Choice(name=lang_label(c)[:100], value=c) for c in matches[:25]]

    # -----------------------
    # /channelselection
    # -----------------------
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(name="channelselection", description="Select channels for auto-translate reaction.")
    async def channelselection(self, interaction: discord.Interaction):
        # Up to 25 options per select; if your server has more, we’d paginate similarly.
        options = [
            discord.SelectOption(label=ch.name, value=str(ch.id))
            for ch in interaction.guild.text_channels[:25]
        ]
        select = discord.ui.Select(
            placeholder="Select channels...",
            min_values=1,
            max_values=len(options) if options else 1,
            options=options or [discord.SelectOption(label="No text channels", value="0", description="")]  # safe-guard
        )

        async def cb(i: discord.Interaction):
            if i.user.id != interaction.user.id:
                return await i.response.defer()
            ids = [int(v) for v in select.values if v.isdigit()]
            await database.set_translation_channels(interaction.guild.id, ids)
            m = ", ".join(f"<#{c}>" for c in ids) if ids else "None"
            await i.response.send_message(f"✅ Channels set: {m}", ephemeral=True)

        select.callback = cb
        view = discord.ui.View(timeout=60)
        view.add_item(select)
        await interaction.response.send_message("Choose channels:", view=view, ephemeral=True)

    # -----------------------
    # /seterrorchannel
    # -----------------------
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(name="seterrorchannel", description="Set or remove error logging channel. Pass 'none' to remove.")
    async def seterrorchannel(self, interaction: discord.Interaction, channel: str):
        gid = interaction.guild.id
        if channel.lower() == "none":
            await database.set_error_channel(gid, None)
            return await interaction.response.send_message("✅ Error channel removed.", ephemeral=True)

        # Accept mention or raw ID
        target = None
        try:
            if channel.startswith("<#") and channel.endswith(">"):
                cid = int(channel[2:-1])
            else:
                cid = int(channel)
            target = interaction.guild.get_channel(cid)
        except Exception:
            target = None

        if not target:
            return await interaction.response.send_message("❌ Invalid channel. Use a mention or channel ID.", ephemeral=True)

        await database.set_error_channel(gid, target.id)
        await interaction.response.send_message(f"✅ Error channel set to {target.mention}", ephemeral=True)

    # -----------------------
    # /emote
    # -----------------------
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(name="emote", description="Set emoji the bot listens for (unicode or custom).")
    async def emote(self, interaction: discord.Interaction, emote: str):
        await database.set_bot_emote(interaction.guild.id, emote)
        await interaction.response.send_message(f"✅ Set bot reaction emote to {emote}", ephemeral=True)

    # -----------------------
    # /settings
    # -----------------------
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.command(name="settings", description="Show current bot settings for this server.")
    async def settings(self, interaction: discord.Interaction):
        gid = interaction.guild.id
        lang = await database.get_server_lang(gid) or "None"
        emote = await database.get_bot_emote(gid) or "🔃"
        err = await database.get_error_channel(gid)
        chans = await database.get_translation_channels(gid)

        embed = discord.Embed(title="🛠️ Server Settings", color=0xDE002A)
        embed.add_field(name="Default Language", value=lang, inline=False)
        embed.add_field(name="Bot Emote", value=emote, inline=False)
        embed.add_field(name="Error Channel", value=(f"<#{err}>" if err else "None"), inline=False)
        embed.add_field(name="Translation Channels", value=", ".join(f"<#{c}>" for c in chans) or "None", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # -----------------------
    # /langlist (pretty grid: flags + names + codes)
    # -----------------------
    @app_commands.command(name="langlist", description="Show supported languages (flags + names + codes).")
    async def langlist(self, interaction: discord.Interaction):
        codes_sorted = sorted(
            SUPPORTED_LANGS,
            key=lambda c: LANG_META.get(c, ("🌐", c.upper()))[1]
        )

        rows = []
        for i in range(0, len(codes_sorted), 3):
            chunk = codes_sorted[i:i + 3]
            cells = [lang_label(code) for code in chunk]
            rows.append("   |   ".join(cells))

        desc = "\n".join(rows)
        embed = discord.Embed(
            title="🌍 Supported Languages",
            description=desc if desc else "No languages configured.",
            color=0xDE002A
        )
        embed.set_footer(text=f"Total: {len(SUPPORTED_LANGS)}")

        await interaction.response.send_message(embed=embed, ephemeral=False)


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))