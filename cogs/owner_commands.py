# cogs/owner_commands.py
import os
import discord
from discord.ext import commands
from discord import app_commands

from utils.brand import COLOR, NAME

def _footer_text():
    try:
        from utils.brand import footer as _f
        return _f() if callable(_f) else str(_f)
    except Exception:
        return f"{NAME} — Developed by Polarix1954"

def _is_owner_id(uid: int, app_owner_id: int | None, env_ids: list[int]) -> bool:
    return uid in env_ids or (app_owner_id is not None and uid == app_owner_id)

class OwnerDashView(discord.ui.View):
    def __init__(self, cog: "OwnerCommands"):
        super().__init__(timeout=120)
        self.cog = cog

    @discord.ui.button(label="Ping", style=discord.ButtonStyle.primary, emoji="🏁")
    async def ping(self, _, interaction: discord.Interaction):
        latency_ms = round(interaction.client.latency * 1000)
        await interaction.response.send_message(f"Pong! `{latency_ms}ms`", ephemeral=True)

    @discord.ui.button(label="Stats", style=discord.ButtonStyle.secondary, emoji="📊")
    async def stats(self, _, interaction: discord.Interaction):
        bot = interaction.client
        guilds = len(bot.guilds)
        users = sum((g.member_count or 0) for g in bot.guilds)
        limit_eur = os.getenv("AI_BUDGET_EUR", "10")
        e = (
            discord.Embed(
                title="📊 Owner Stats",
                description=(
                    f"Servers: **{guilds}**\n"
                    f"Users (approx): **{users}**\n"
                    f"AI budget limit: **€{limit_eur}**\n"
                ),
                color=COLOR,
            ).set_footer(text=_footer_text())
        )
        await interaction.response.send_message(embed=e, ephemeral=True)

    @discord.ui.button(label="Guilds", style=discord.ButtonStyle.secondary, emoji="🧭")
    async def guilds(self, _, interaction: discord.Interaction):
        lines = []
        for g in sorted(interaction.client.guilds, key=lambda x: x.member_count or 0, reverse=True)[:20]:
            lines.append(f"• **{g.name}** — {g.member_count} users (id `{g.id}`)")
        e = discord.Embed(title="🧭 Guilds (Top 20)", description="\n".join(lines) or "None", color=COLOR).set_footer(text=_footer_text())
        await interaction.response.send_message(embed=e, ephemeral=True)

    @discord.ui.button(label="Reload Cogs", style=discord.ButtonStyle.danger, emoji="🔁")
    async def reload(self, _, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        bot: commands.Bot = interaction.client
        failed, reloaded = [], []
        for ext in list(bot.extensions.keys()):
            try:
                await bot.reload_extension(ext)
                reloaded.append(ext)
            except Exception:
                failed.append(ext)
        msg = f"🔁 Reloaded: {len(reloaded)} | ❌ Failed: {len(failed)}"
        await interaction.followup.send(msg, ephemeral=True)

class OwnerCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        env = os.getenv("OWNER_IDS", "")
        try:
            self._owner_ids_env = [int(x) for x in env.replace(" ", "").split(",") if x]
        except Exception:
            self._owner_ids_env = []
        self._app_owner_id: int | None = None  # cached later

    async def _get_app_owner_id(self) -> int | None:
        if self._app_owner_id is not None:
            return self._app_owner_id
        try:
            appinfo = await self.bot.application_info()
            self._app_owner_id = appinfo.owner.id if appinfo and appinfo.owner else None
        except Exception:
            self._app_owner_id = None
        return self._app_owner_id

    async def _owner_check(self, interaction: discord.Interaction) -> bool:
        app_owner = await self._get_app_owner_id()
        return _is_owner_id(interaction.user.id, app_owner, self._owner_ids_env)

    def _ensure_owner(self):
        async def predicate(interaction: discord.Interaction):
            return await self._owner_check(interaction)
        return app_commands.check(predicate)

    @app_commands.command(name="owner", description="Owner dashboard with buttons.")
    async def owner(self, interaction: discord.Interaction):
        if not await self._owner_check(interaction):
            return await interaction.response.send_message("Nope.", ephemeral=True)
        view = OwnerDashView(self)
        e = discord.Embed(
            title="🛡 Owner Dashboard",
            description="Use the buttons below: **Ping**, **Stats**, **Guilds**, **Reload Cogs**.",
            color=COLOR
        ).set_footer(text=_footer_text())
        await interaction.response.send_message(embed=e, view=view, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(OwnerCommands(bot))
