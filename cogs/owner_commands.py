# cogs/owner_commands.py
import discord
from discord.ext import commands
from discord import app_commands
import traceback

try:
    from utils.brand import COLOR
except Exception:
    COLOR = 0x00E6F6
try:
    from utils.brand import FOOTER as BRAND_FOOTER
except Exception:
    BRAND_FOOTER = "Zephyra • /help for commands"

def owner_check():
    async def predicate(inter: discord.Interaction) -> bool:
        app_info = await inter.client.application_info()
        try:
            if hasattr(app_info.owner, "id"):
                return app_info.owner.id == inter.user.id
        except Exception:
            pass
        return False
    return app_commands.check(predicate)

class OwnerDashView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=120)
        self.bot = bot

    @discord.ui.Button(label="Ping", emoji="🏁", style=discord.ButtonStyle.primary)
    async def ping(self, interaction: discord.Interaction, button: discord.ui.Button):
        latency_ms = round(self.bot.latency * 1000)
        e = discord.Embed(description=f"🏁 Latency: **{latency_ms} ms**", color=COLOR)
        e.set_footer(text=BRAND_FOOTER)
        await interaction.response.edit_message(embed=e, view=self)

    @discord.ui.Button(label="Stats", emoji="📊", style=discord.ButtonStyle.secondary)
    async def stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        users = sum((g.member_count or 0) for g in self.bot.guilds)
        e = discord.Embed(description=f"📊 Servers: **{len(self.bot.guilds)}**\n👥 Approx users: **{users}**", color=COLOR)
        e.set_footer(text=BRAND_FOOTER)
        await interaction.response.edit_message(embed=e, view=self)

    @discord.ui.Button(label="Guilds", emoji="🧭", style=discord.ButtonStyle.secondary)
    async def guilds(self, interaction: discord.Interaction, button: discord.ui.Button):
        lines = []
        for g in sorted(self.bot.guilds, key=lambda x: x.member_count or 0, reverse=True)[:20]:
            lines.append(f"• **{g.name}** — {g.member_count or 0} members (id: `{g.id}`)")
        e = discord.Embed(title="🧭 Top Guilds", description="\n".join(lines) or "None", color=COLOR)
        e.set_footer(text=BRAND_FOOTER)
        await interaction.response.edit_message(embed=e, view=self)

    @discord.ui.Button(label="Reload Cogs", emoji="🔁", style=discord.ButtonStyle.danger)
    async def reload(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        failed = []
        for ext in list(interaction.client.extensions.keys()):
            try:
                await interaction.client.reload_extension(ext)
            except Exception:
                failed.append(f"{ext}\n{traceback.format_exc(limit=1)}")
        text = "✅ Reloaded all cogs." if not failed else "⚠️ Reload complete with errors:\n" + "\n".join(failed)
        await interaction.followup.send(text, ephemeral=True)

class OwnerCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @owner_check()
    @app_commands.command(name="owner", description="Owner dashboard (buttons).")
    async def owner(self, interaction: discord.Interaction):
        e = discord.Embed(title="👑 Owner Dashboard", description="Use the buttons below.", color=COLOR)
        e.set_footer(text=BRAND_FOOTER)
        await interaction.response.send_message(embed=e, view=OwnerDashView(self.bot), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(OwnerCommands(bot))
