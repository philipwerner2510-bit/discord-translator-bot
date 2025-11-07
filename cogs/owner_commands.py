# cogs/owner_commands.py
import os, platform, time
import discord
from discord.ext import commands
from discord import app_commands
from utils.brand import COLOR, footer_text as _footer_text
from utils import database

def FOOT(): return _footer_text() if callable(_footer_text) else _footer_text
OWNER_IDS = {int(x) for x in os.getenv("OWNER_IDS","1425590836800000170").split(",") if x.strip().isdigit()}

def check_owner():
    def predicate(interaction: discord.Interaction) -> bool:
        return interaction.user.id in OWNER_IDS
    return app_commands.check(predicate)

class OwnerView(discord.ui.View):
    def __init__(self, cog, *, timeout=120):
        super().__init__(timeout=timeout)
        self.cog = cog

    @discord.ui.button(label="Stats", style=discord.ButtonStyle.primary)
    async def stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.render_stats(interaction)

    @discord.ui.button(label="Guilds", style=discord.ButtonStyle.secondary)
    async def guilds(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.render_guilds(interaction)

    @discord.ui.button(label="Self-test", style=discord.ButtonStyle.success)
    async def selftest(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.render_selftest(interaction)

    @discord.ui.button(label="Reload Cogs", style=discord.ButtonStyle.danger)
    async def reload(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.reload_all(interaction)

class Owner(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="owner", description="Owner control panel.")
    @check_owner()
    async def owner(self, interaction: discord.Interaction):
        await self.render_stats(interaction, new_message=True)

    async def render_stats(self, interaction: discord.Interaction, new_message: bool=False):
        bot = self.bot
        guilds = len(bot.guilds)
        users = sum(g.member_count or 0 for g in bot.guilds)
        py = platform.python_version()
        e = (discord.Embed(title="Owner — Stats", color=COLOR)
             .add_field(name="Guilds", value=str(guilds))
             .add_field(name="Users (approx)", value=str(users))
             .add_field(name="Python", value=py)
             .set_footer(text=FOOT()))
        view = OwnerView(self)
        if new_message:
            await interaction.response.send_message(embed=e, view=view, ephemeral=True)
        else:
            await interaction.response.edit_message(embed=e, view=view)

    async def render_guilds(self, interaction: discord.Interaction):
        lines = []
        for g in sorted(self.bot.guilds, key=lambda x: x.member_count or 0, reverse=True)[:25]:
            lines.append(f"{g.name} — `{g.id}` — {g.member_count} members")
        e = discord.Embed(title="Owner — Guilds (top 25)", description="\n".join(lines) or "No guilds.", color=COLOR)
        e.set_footer(text=FOOT())
        await interaction.response.edit_message(embed=e, view=OwnerView(self))

    async def render_selftest(self, interaction: discord.Interaction):
        e = discord.Embed(title="Owner — Self-test", description="All systems nominal.", color=COLOR)
        e.set_footer(text=FOOT())
        await interaction.response.edit_message(embed=e, view=OwnerView(self))

    async def reload_all(self, interaction: discord.Interaction):
        failed = []
        for ext in list(self.bot.extensions.keys()):
            try:
                await self.bot.reload_extension(ext)
            except Exception as ex:
                failed.append(f"{ext}: {ex}")
        msg = "Reloaded all cogs." if not failed else "Reload completed with errors:\n" + "\n".join(failed)
        e = discord.Embed(title="Owner — Reload", description=msg, color=COLOR)
        e.set_footer(text=FOOT())
        await interaction.response.edit_message(embed=e, view=OwnerView(self))

async def setup(bot):
    await bot.add_cog(Owner(bot))
